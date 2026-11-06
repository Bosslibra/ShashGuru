# This file is part of ShashGuru. Copyright (C) 2025 Alessandro Libralesso.
# Licensed under the GNU GPL v3 or later, see COPYING.
import io
import logging
import math
import queue
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import chess
import chess.engine
import chess.pgn

from app.config import Settings
from app.services.engine_cache import EngineCache

log = logging.getLogger(__name__)

ENGINE_FILES = {"NNUE": "shashchess", "HUMAN": "alexander"}


class EngineUnavailable(RuntimeError):
    """No engine could be obtained from the pool."""


class EnginePool:
    """A pool of UCI engine processes driven through python-chess."""

    def __init__(self, path: str, size: int, threads: int, hash_mb: int):
        self.path = path
        self.size = size
        self.threads = threads
        self.hash_mb = hash_mb
        self._available: "queue.Queue[chess.engine.SimpleEngine]" = queue.Queue()
        self._closed = False
        for i in range(size):
            try:
                self._available.put(self._create())
            except Exception as e:
                log.error("Failed to start engine %d/%d (%s): %s", i + 1, size, path, e)
        log.info("Engine pool %s ready: %d/%d engines", path, self._available.qsize(), size)

    def _create(self) -> chess.engine.SimpleEngine:
        engine = chess.engine.SimpleEngine.popen_uci(self.path)
        options: dict[str, Any] = {"Threads": self.threads, "Hash": self.hash_mb}
        if "UCI_ShowWDL" in engine.options:
            options["UCI_ShowWDL"] = True
        engine.configure({k: v for k, v in options.items() if k in engine.options})
        return engine

    @staticmethod
    def _alive(engine: chess.engine.SimpleEngine) -> bool:
        # protocol.returncode is a Future that completes when the process exits
        return not engine.protocol.returncode.done()

    @contextmanager
    def acquire(self, timeout: float = 30) -> Iterator[chess.engine.SimpleEngine]:
        if self._closed:
            raise EngineUnavailable("Engine pool is shut down")
        try:
            engine = self._available.get(timeout=timeout)
        except queue.Empty:
            raise EngineUnavailable("No engine available") from None
        if not self._alive(engine):
            log.warning("Engine died, replacing it")
            try:
                engine = self._create()
            except Exception as e:
                raise EngineUnavailable(f"Cannot restart engine: {e}") from e
        healthy = True
        try:
            yield engine
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError):
            healthy = False
            raise
        finally:
            if healthy and self._alive(engine) and not self._closed:
                self._available.put(engine)
            else:
                self._discard(engine)
                if not self._closed:
                    try:
                        self._available.put(self._create())
                    except Exception as e:
                        log.error("Cannot replace engine: %s", e)

    @staticmethod
    def _discard(engine: chess.engine.SimpleEngine) -> None:
        try:
            engine.quit()
        except Exception:
            try:
                engine.close()
            except Exception:
                pass

    def shutdown(self) -> None:
        self._closed = True
        while True:
            try:
                self._discard(self._available.get_nowait())
            except queue.Empty:
                break

    def stats(self) -> dict[str, Any]:
        available = self._available.qsize()
        return {"initialized": True, "pool_size": self.size, "available": available, "busy": self.size - available}


def _normalize_line(rank: int, info: chess.engine.InfoDict, board: chess.Board) -> Optional[dict[str, Any]]:
    pv = [m.uci() for m in info.get("pv", [])]
    if not pv or "score" not in info:
        return None
    score = info["score"].pov(board.turn)
    wdl = None
    winprob = None
    if "wdl" in info:
        w, d, l = info["wdl"].pov(board.turn)
        wdl = {"w": w, "d": d, "l": l}
        winprob = (w + d / 2) / 10
    elif score.is_mate():
        winprob = 100.0 if score.mate() > 0 else 0.0
    else:
        # Engines without WDL output: standard logistic mapping of centipawns.
        winprob = 100 / (1 + math.exp(-0.00368208 * score.score()))
    return {
        "rank": rank,
        "move": pv[0],
        "pv": pv,
        "score": {"cp": score.score() if not score.is_mate() else None, "mate": score.mate()},
        "wdl": wdl,
        "winprob": winprob,
        "depth": info.get("depth", 0),
    }


def _terminal_status(board: chess.Board) -> Optional[str]:
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_insufficient_material():
        return "draw"
    return None


class EngineService:
    """Facade used by the API: pools, cache and analysis helpers."""

    def __init__(self, settings: Settings, cache: EngineCache):
        self.settings = settings
        self.cache = cache
        self._pools: dict[str, EnginePool] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        """Warm up the NNUE pool (the HUMAN one is created on first use)."""
        self._pool("NNUE")

    def shutdown(self) -> None:
        with self._lock:
            for pool in self._pools.values():
                pool.shutdown()
            self._pools.clear()

    def _pool(self, name: str) -> EnginePool:
        with self._lock:
            pool = self._pools.get(name)
            if pool is None:
                s = self.settings
                pool = EnginePool(s.engine_path(ENGINE_FILES[name]), s.engine_pool_size,
                                  s.threads_per_engine, s.engine_hash_mb)
                self._pools[name] = pool
            return pool

    def pool_stats(self) -> dict[str, Any]:
        stats: dict[str, Any] = {}
        for name in ENGINE_FILES:
            pool = self._pools.get(name)
            stats[name] = pool.stats() if pool else {"initialized": False}
        return stats

    # -- analysis ---------------------------------------------------------

    def _analyse_with(self, engine: chess.engine.SimpleEngine, name: str, fen: str,
                      depth: int, lines: int) -> dict[str, Any]:
        board = chess.Board(fen)
        status = _terminal_status(board)
        if status:
            return {"status": status, "depth": 0, "lines": [], "ponder": None}

        cached = self.cache.get(name, fen, depth, lines)
        if cached:
            return cached

        legal = board.legal_moves.count()
        infos = engine.analyse(
            board,
            chess.engine.Limit(depth=depth, time=self.settings.analysis_timeout),
            multipv=min(lines, legal),
            info=chess.engine.INFO_ALL,
        )
        if isinstance(infos, dict):
            infos = [infos]
        result_lines = [l for i, info in enumerate(infos, 1) if (l := _normalize_line(i, info, board))]
        reached = min((l["depth"] for l in result_lines), default=0)
        ponder = result_lines[0]["pv"][1] if result_lines and len(result_lines[0]["pv"]) > 1 else None
        result = {"status": "ok", "depth": reached, "lines": result_lines, "ponder": ponder}
        if result_lines:
            self.cache.put(name, fen, reached, lines, result)
        return result

    def analyse(self, name: str, fen: str, depth: int, lines: int) -> dict[str, Any]:
        """Blocking: call from a worker thread."""
        with self._pool(name).acquire() as engine:
            return self._analyse_with(engine, name, fen, depth, lines)

    def analyse_game(self, name: str, source: "str | list[str]", depth: int, lines: int) -> list[dict[str, Any]]:
        """Analyse every position of a game with a single engine. Blocking."""
        board = chess.Board()
        if isinstance(source, str):
            game = chess.pgn.read_game(io.StringIO(source))
            if game is None or not list(game.mainline_moves()):
                raise ValueError("Invalid or empty PGN")
            moves = [m.uci() for m in game.mainline_moves()]
            board = game.board()
        else:
            moves = source

        positions: list[dict[str, Any]] = []
        with self._pool(name).acquire(timeout=60) as engine:
            def add(number: int, played: Optional[str]) -> None:
                fen = board.fen()
                result = self._analyse_with(engine, name, fen, depth, lines)
                positions.append({
                    "move_number": number, "fen": fen, "move_played": played,
                    "analysis": _to_evaluation(fen, result),
                })

            add(0, None)
            for number, uci in enumerate(moves, 1):
                try:
                    move = chess.Move.from_uci(uci)
                except ValueError:
                    raise ValueError(f"Invalid move '{uci}' at ply {number}") from None
                if move not in board.legal_moves:
                    raise ValueError(f"Illegal move '{uci}' at ply {number}")
                board.push(move)
                add(number, uci)
        return positions


def _to_evaluation(fen: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "fen": fen,
        "sideToMove": "white" if fen.split()[1] == "w" else "black",
        "status": result["status"],
        "depth": result["depth"],
        "lines": result["lines"],
    }


to_evaluation = _to_evaluation

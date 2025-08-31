import { ref } from "vue";

const LiveChessAPIURL = "ws://127.0.0.1:1982/api/v1.0";

const IDS = {
  serials: 48617, // arbitrary value for board discovery
};

let callCounter = 100; // unique ids for setup/flip calls

const METHODS = {
  subscription: (id, feedId, serial) =>
    JSON.stringify({
      call: "subscribe",
      id,
      param: {
        feed: "eboardevent",
        id: feedId,
        param: { serialnr: serial },
      },
    }),
  eboards: (id) =>
    JSON.stringify({
      call: "eboards",
      id,
      param: null,
    }),
  setup: (feedId, fen) =>
    JSON.stringify({
      id: ++callCounter,
      call: "call",
      param: {
        id: feedId,
        method: "setup",
        param: { fen },
      },
    }),
  flip: (feedId, flip) =>
    JSON.stringify({
      id: ++callCounter,
      call: "call",
      param: {
        id: feedId,
        method: "flip",
        param: { flip },
      },
    }),
};

export function useDGT() {
  const active = ref(false);
  const lastMove = ref(""); // latest SAN move
  const position = ref(""); // latest board FEN
  const clock = ref(null);  // clock updates
  const moves = ref([]);    // SAN move list
  const match = ref(false); // whether board matches SAN reconstruction
  let connection = null;

  // Track boards subscribed
  const subscribedBoards = new Map();

  const connect = () => {
    if (connection && connection.readyState === WebSocket.OPEN) return;

    connection = new WebSocket(LiveChessAPIURL);

    connection.onopen = () => {
      console.log("DGT: connection open");
      active.value = true;
      connection.send(METHODS.eboards(IDS.serials));
    };

    connection.onerror = (error) => {
      console.error("DGT: connection error", error);
    };

    connection.onmessage = (response) => {
      const message = JSON.parse(response.data);
      console.log("DGT: message received", message);

      // Step 1: list boards
      if (message.id === IDS.serials) {
        message.param.forEach(({ serialnr }, index) => {
          if (serialnr) {
            const feedId = index + 1;
            const subscription = METHODS.subscription(feedId, feedId, serialnr);
            subscribedBoards.set(feedId, { serialnr, fen: null });
            connection.send(subscription);
          }
        });
      }

      // Step 2: feed updates
      if (message.response === "feed") {
        
        const feedId = message.id;
        const param = message.param;
        console.log("PARAM", param)
        console.log(param.san)
        if (param.board) {
          position.value = param.board;
        }

        if (param.clock) {
          clock.value = param.clock;
        }

        if (param.san) {
          moves.value = param.san;
          lastMove.value = param.san[param.san.length - 1] || "";
        }

        if (param.match !== undefined) {
          match.value = param.match;
        }
      }
    };

    connection.onclose = () => {
      console.log("DGT: connection closed");
      active.value = false;
    };
  };

  const disconnect = () => {
    if (connection) {
      connection.close();
      connection = null;
      active.value = false;
    }
  };

  const setup = (feedId, fen) => {
    if (connection && connection.readyState === WebSocket.OPEN) {
      connection.send(METHODS.setup(feedId, fen));
      const board = subscribedBoards.get(feedId);
      if (board) board.fen = fen;
    }
  };

  const flip = (feedId, flipped = true) => {
    if (connection && connection.readyState === WebSocket.OPEN) {
      connection.send(METHODS.flip(feedId, flipped));
    }
  };

  return {
    active,
    lastMove,
    moves,
    position,
    clock,
    match,
    connect,
    disconnect,
    setup,
    flip,
  };
}

<template>
  <div class="about">
    <div class="fs-4 m-auto mt-5 w-50">
      <p>
        This is <strong>ShashGuru</strong>, a chess analyzer that takes a FEN or a PGN, asks a UCI chess engine to
        analyse it, and then outputs a natural language analysis made by an LLM.
      </p>
    </div>
  </div>
<footer class="text-light py-4 mt-5 border-top">
  <div class="container">
    <p class="mb-2">
      &copy; 2025 <strong>Alessandro Libralesso</strong>
    </p>

    <p class="mb-2">
      <strong>ShashGuru</strong> is free software: you can redistribute it and/or modify it under the terms of the
      <a href="https://www.gnu.org/licenses/gpl-3.0.en.html" class="" target="_blank" rel="noopener noreferrer">
        GNU General Public License
      </a>, version 3 or (at your option) any later version.
    </p>

    <p class="mb-2">
      ShashGuru is distributed in the hope that it will be useful, but
      <strong>WITHOUT ANY WARRANTY</strong>; without even the implied warranty of
      <em>MERCHANTABILITY</em> or <em>FITNESS FOR A PARTICULAR PURPOSE</em>.
    </p>

    <p class="mb-0">
      You should have received a copy of the GNU General Public License along with this program.
      If not, visit
      <a href="https://www.gnu.org/licenses/gpl-3.0.en.html" class="" target="_blank" rel="noopener noreferrer">
        www.gnu.org/licenses
      </a>.
    </p>
  </div>
</footer>

</template>

<style>
@media (min-width: 1024px) {
  .about {
    min-height: 100vh;
    display: flex;
    align-items: center;
  }
}

</style>
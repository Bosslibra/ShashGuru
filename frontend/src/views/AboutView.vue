<template>
  <div class="about">
    <div class="fs-4 m-auto mt-5 w-50">
  <p>
    This is <strong>ShashGuru</strong>, a chess analyzer that takes a FEN, asks a UCI chess engine to
    analyse it, and then outputs a natural language analysis made by an LLM.
  </p>

  <p>
    &copy; 2025 Alessandro Libralesso
  </p>

  <p>
    ShashGuru is free software: you can redistribute it and/or modify
    it under the terms of the <strong>GNU General Public License</strong> as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
  </p>

  <p>
    ShashGuru is distributed in the hope that it will be useful,
    but <strong>WITHOUT ANY WARRANTY</strong>; without even the implied warranty of
    <em>MERCHANTABILITY</em> or <em>FITNESS FOR A PARTICULAR PURPOSE</em>.
    See the GNU General Public License for more details.
  </p>

  <p>
    You should have received a copy of the GNU General Public License
    along with this program. If not, see
    <a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank" rel="noopener noreferrer">
      www.gnu.org/licenses
    </a>.
  </p>
</div>
  </div>
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

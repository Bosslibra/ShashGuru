<template>
    <div id="eventGameCard" class="rounded m-3 p-2 placeholder-glow">
        <div class="d-flex justify-content-between align-items-center">
            <span class="placeholder col-2 me-1"></span>
            <span class="placeholder col-4"></span>
            <span class="placeholder col-2 ms-auto"></span>
            <span class="placeholder col-1 ms-3"></span>
        </div>

        <div class="placeholder my-2" style="height:250px; width:250px;"></div>

        <div class="d-flex justify-content-between align-items-center">
            <span class="placeholder col-2 me-1"></span>
            <span class="placeholder col-4"></span>
            <span class="placeholder col-2 ms-auto"></span>
            <span class="placeholder col-1 ms-3"></span>
        </div>
    </div>
</template>

<script setup lang="ts">
// No script logic is needed for this simple skeleton component.
</script>

<style scoped>
#eventGameCard {
    width: 270px;
    color: #ddd;
    background-color: #262421;
    border: 1px solid #262421;
    transition: 0.3s;
}
</style>
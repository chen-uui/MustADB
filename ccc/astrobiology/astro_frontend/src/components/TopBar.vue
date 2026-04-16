<template>
  <div id="topbar" class="hidden md:flex items-center justify-between px-6 h-10 border-b border-nebula-purple/30 fixed top-0 left-0 w-full z-50 text-xs uppercase tracking-wider text-white/60 font-mono">
    <div class="flex items-center gap-4">
      <span class="flex items-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
        System Online
      </span>
      <span>v2.0.1-beta</span>
    </div>
    <div class="flex items-center gap-4">
      <span>Macau University of Science and Technology</span>
      <span class="text-starlight-blue/50">Secure Connection</span>
    </div>
  </div>
</template>

<script setup>
// TopBar component - System Status
</script>

<style>
/* Remove all background - let the starfield show through */
#topbar {
  background: transparent !important;
  backdrop-filter: blur(2px);
}

/* Add a subtle text shadow for readability */
#topbar span {
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
}
</style>

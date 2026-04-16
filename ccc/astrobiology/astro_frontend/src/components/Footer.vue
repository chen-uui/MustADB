<template>
  <footer id="footer" class="relative z-10 border-t border-white/5 !bg-space-black/50 backdrop-blur-sm pt-16 pb-8">
    <div class="container mx-auto px-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-12 mb-12">
        <!-- Footer Info -->
        <div class="space-y-6 animate-fade-in-up">
          <h3 class="text-xl font-bold text-white tracking-tight">
            MUSTADB
          </h3>
          <p class="text-white/50 text-sm leading-relaxed font-light">
            Avenida Wai Long, Taipa, Macau<br>
            <span class="block mt-2">
              <strong class="text-white/70">Phone:</strong> +86 13184850985
            </span>
            <span class="block">
              <strong class="text-white/70">Email:</strong> cbh1940492031@outlook.com
            </span>
          </p>
        </div>

        <!-- Useful Links -->
        <div class="space-y-6 animate-fade-in-up delay-100">
          <h4 class="text-lg font-semibold text-white relative inline-block pb-2 after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-12 after:h-0.5 after:bg-starlight-blue">
            Useful Links
          </h4>
          <ul class="space-y-3">
            <li>
              <a href="#hero" class="text-white/50 hover:text-starlight-blue hover:pl-2 transition-all duration-300 block text-sm">Home</a>
            </li>
            <li>
              <a href="#about" class="text-white/50 hover:text-starlight-blue hover:pl-2 transition-all duration-300 block text-sm">About us</a>
            </li>
            <li>
              <a href="/meteorite-search" class="text-white/50 hover:text-starlight-blue hover:pl-2 transition-all duration-300 block text-sm">Meteorite Search</a>
            </li>
          </ul>
        </div>

        <!-- Newsletter -->
        <div class="space-y-6 animate-fade-in-up delay-200">
          <h4 class="text-lg font-semibold text-white relative inline-block pb-2 after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-12 after:h-0.5 after:bg-starlight-blue">
            Our Mission
          </h4>
          <p class="text-white/50 text-sm leading-relaxed font-light">
            Committed to providing the largest, most complete and most convenient database services for extraterrestrial organic matter research.
          </p>
        </div>
      </div>

      <!-- Copyright -->
      <div class="border-t border-white/5 pt-8 text-center animate-fade-in-up delay-300">
        <div class="text-white/30 text-xs font-light">
          CPU © Pharmaceutical Big Data And Artificial Intelligence Joint Laboratory
          <span class="mx-2">|</span>
          <a href="https://beian.miit.gov.cn" class="hover:text-starlight-blue transition-colors">苏ICP备2023023603号-3</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
// Footer component
</script>

<style scoped>
.delay-100 { animation-delay: 0.1s; }
.delay-200 { animation-delay: 0.2s; }
.delay-300 { animation-delay: 0.3s; }
</style>

<template>
  <section id="about" class="py-20 relative">
    <div class="container mx-auto px-6 relative z-10">
      <div class="text-center mb-16" v-scroll-animate="'animate-fade-in-up'">
        <h2 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
          About Us
        </h2>
        <p class="text-lg text-white/60 max-w-2xl mx-auto font-light">
          MUSTADB is a comprehensive astrobiology database system designed to facilitate research and exploration of extraterrestrial organic matter.
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        <!-- Image Side -->
        <div class="relative group" v-scroll-animate="'animate-scale-in'">
          <div class="absolute -inset-1 bg-gradient-to-r from-nebula-purple to-starlight-blue rounded-2xl blur opacity-30 group-hover:opacity-60 transition duration-1000"></div>
          <div class="relative rounded-2xl overflow-hidden border border-white/10">
            <img :src="aboutImage" class="w-full h-auto transform group-hover:scale-105 transition duration-700" alt="About Image">
            <div class="absolute inset-0 bg-space-black/20 group-hover:bg-transparent transition duration-500"></div>
          </div>
        </div>

        <!-- Content Side -->
        <div class="space-y-8" v-scroll-animate="'animate-fade-in-up'">
          <AstroCard class="bg-white/5 backdrop-blur-md border-white/10">
            <p class="text-white/80 leading-relaxed mb-6 text-lg font-light">
              MUSTADB (Meteorite and Extraterrestrial Organic Matter Database) is an advanced astrobiology database platform that provides researchers and scientists with comprehensive tools for exploring and analyzing meteorite data, organic compounds, and related scientific information.
            </p>
            
            <h3 class="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <i class="bi bi-stars text-starlight-blue"></i>
              Key Features
            </h3>
            
            <ul class="space-y-4">
              <li class="flex items-start gap-3 group">
                <i class="bi bi-check-circle-fill text-starlight-blue mt-1 group-hover:scale-110 transition-transform"></i>
                <span class="text-white/70 group-hover:text-white transition-colors">Advanced meteorite search and data retrieval</span>
              </li>
              <li class="flex items-start gap-3 group">
                <i class="bi bi-check-circle-fill text-starlight-blue mt-1 group-hover:scale-110 transition-transform"></i>
                <span class="text-white/70 group-hover:text-white transition-colors">AI-powered intelligent Q&A system</span>
              </li>
              <li class="flex items-start gap-3 group">
                <i class="bi bi-check-circle-fill text-starlight-blue mt-1 group-hover:scale-110 transition-transform"></i>
                <span class="text-white/70 group-hover:text-white transition-colors">Comprehensive document management and processing</span>
              </li>
              <li class="flex items-start gap-3 group">
                <i class="bi bi-check-circle-fill text-starlight-blue mt-1 group-hover:scale-110 transition-transform"></i>
                <span class="text-white/70 group-hover:text-white transition-colors">Automated data extraction and analysis tools</span>
              </li>
            </ul>
          </AstroCard>
          
          <p class="text-white/60 italic border-l-4 border-starlight-blue pl-4">
            "Our platform integrates cutting-edge AI technology with extensive scientific databases to provide researchers with powerful tools for astrobiology research and discovery."
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import aboutImage from '../assets/img/mars_image_1.png';
import AstroCard from './ui/AstroCard.vue';
</script>

<style scoped>
.delay-100 { animation-delay: 0.1s; }
.delay-200 { animation-delay: 0.2s; }
</style>

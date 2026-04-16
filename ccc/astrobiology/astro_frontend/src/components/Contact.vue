<template>
  <section id="contact" class="py-20 relative">
    <div class="container mx-auto px-6 relative z-10">
      <div class="text-center mb-16" v-scroll-animate="'animate-fade-in-up'">
        <h2 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
          Contact Us
        </h2>
        <p class="text-lg text-white/60 max-w-2xl mx-auto font-light">
          We welcome your inquiries and collaboration. Reach out to us through any of the channels below.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- Address -->
        <AstroCard class="text-center group" v-scroll-animate="'animate-scale-in'">
          <div class="w-16 h-16 mx-auto rounded-full bg-white/5 flex items-center justify-center mb-6 group-hover:bg-starlight-blue/20 transition-colors">
            <i class="bi bi-geo-alt text-3xl text-starlight-blue"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">Our Address</h3>
          <p class="text-white/60">Avenida Wai Long, Taipa, Macau</p>
        </AstroCard>

        <!-- Email -->
        <AstroCard class="text-center group" v-scroll-animate="'animate-scale-in'">
          <div class="w-16 h-16 mx-auto rounded-full bg-white/5 flex items-center justify-center mb-6 group-hover:bg-starlight-blue/20 transition-colors">
            <i class="bi bi-envelope text-3xl text-starlight-blue"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">Email Us</h3>
          <p class="text-white/60">cbh1940492031@outlook.com</p>
        </AstroCard>

        <!-- Phone -->
        <AstroCard class="text-center group" v-scroll-animate="'animate-scale-in'">
          <div class="w-16 h-16 mx-auto rounded-full bg-white/5 flex items-center justify-center mb-6 group-hover:bg-starlight-blue/20 transition-colors">
            <i class="bi bi-telephone text-3xl text-starlight-blue"></i>
          </div>
          <h3 class="text-xl font-bold text-white mb-2">Call Us</h3>
          <p class="text-white/60">+86 13184850985</p>
        </AstroCard>
      </div>
    </div>
  </section>
</template>

<script setup>
import AstroCard from './ui/AstroCard.vue';
</script>

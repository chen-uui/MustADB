<template>
  <section class="relative min-h-screen flex items-center justify-center pt-20 md:pt-32 overflow-hidden">
    <div class="container mx-auto px-6 text-center z-10">
      <!-- Version Badge -->
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-glass-border bg-white/5 backdrop-blur-md mb-8 animate-fade-in-up">
        <span class="w-2 h-2 rounded-full bg-starlight-blue animate-pulse-slow"></span>
        <span class="text-xs font-medium tracking-wide uppercase text-white/60">System v2.0 Online</span>
      </div>
      
      <!-- Main Title -->
      <h1 class="text-6xl md:text-8xl font-extralight tracking-tighter mb-8 leading-[1.1] animate-fade-in-up delay-100">
        Explore the <br />
        <span class="font-normal animated-gradient-text">Origins of Life.</span>
      </h1>
      
      <!-- Subtitle -->
      <p class="text-xl md:text-2xl text-white/50 font-light max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-in-up delay-200">
        The Extraterrestrial Organic Matter Database System. <br/>
        Advanced analysis for meteorite samples and scientific documents.
      </p>
      
      <!-- CTA Buttons -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in-up delay-300">
        <AstroButton variant="primary" size="lg" @click="scrollToWorkspace" class="group">
          <i class="bi bi-rocket-takeoff mr-2 group-hover:rotate-12 transition-transform"></i>
          Start Exploration
        </AstroButton>
        
        <AstroButton variant="secondary" size="lg" @click="scrollToUpload" class="group">
          <i class="bi bi-cloud-upload mr-2 group-hover:-translate-y-1 transition-transform"></i>
          Upload Data
        </AstroButton>
      </div>
    </div>
  </section>
</template>

<script setup>
import AstroButton from './ui/AstroButton.vue'

const scrollToWorkspace = () => {
  const element = document.getElementById('workspace-entrance')
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}

const scrollToUpload = () => {
  const element = document.getElementById('pdf-upload')
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

<style scoped>
.delay-100 { animation-delay: 0.1s; }
.delay-200 { animation-delay: 0.2s; }
.delay-300 { animation-delay: 0.3s; }

.animated-gradient-text {
  background: linear-gradient(120deg, #ffffff 0%, #00CEC9 30%, #6C5CE7 60%, #ffffff 100%);
  background-size: 200% auto;
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradient-shift 4s ease-in-out infinite;
}

@keyframes gradient-shift {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}
</style>
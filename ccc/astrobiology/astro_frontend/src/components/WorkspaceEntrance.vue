<template>
  <section id="workspace-entrance" class="py-20 relative overflow-hidden">
    <div class="container mx-auto px-6 relative z-10">
      <div class="text-center mb-16 animate-fade-in-up">
        <h2 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
          Intelligent Workspace
        </h2>
        <p class="text-lg text-white/60 max-w-2xl mx-auto font-light">
          Access our advanced research tools and AI-powered features for deep space analysis.
        </p>
      </div>
      
      <div class="max-w-5xl mx-auto">
        <AstroCard 
          class="group cursor-pointer transform hover:-translate-y-2 transition-all duration-500 !p-0 overflow-hidden border-starlight-blue/20 hover:border-starlight-blue/50"
          @click="navigateToWorkspace"
        >
          <div class="flex flex-col md:flex-row min-h-[400px]">
            <!-- Left Side: Visual & Icon -->
            <div class="w-full md:w-2/5 bg-gradient-to-br from-nebula-purple/20 to-starlight-blue/10 relative p-10 flex flex-col items-center justify-center overflow-hidden">
              <!-- Animated Background Elements -->
              <div class="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(108,92,231,0.2),transparent_70%)] animate-pulse-slow"></div>
              
              <!-- Icon Wrapper -->
              <div class="relative z-10 w-24 h-24 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 flex items-center justify-center mb-8 group-hover:scale-110 group-hover:rotate-3 transition-all duration-500 shadow-[0_0_30px_rgba(108,92,231,0.3)]">
                <i class="bi bi-stars text-4xl text-starlight-blue"></i>
              </div>
              
              <!-- Features List -->
              <div class="space-y-4 relative z-10">
                <div class="flex items-center gap-3 text-white/80">
                  <i class="bi bi-check-circle-fill text-starlight-blue"></i>
                  <span class="font-medium">Meteorite Search</span>
                </div>
                <div class="flex items-center gap-3 text-white/80">
                  <i class="bi bi-check-circle-fill text-starlight-blue"></i>
                  <span class="font-medium">AI-Powered Q&A</span>
                </div>
              </div>
            </div>
            
            <!-- Right Side: Content -->
            <div class="w-full md:w-3/5 p-10 md:p-12 flex flex-col justify-center bg-space-black/40 backdrop-blur-sm">
              <h3 class="text-3xl font-bold text-white mb-6 group-hover:text-starlight-blue transition-colors">
                Explore Our Database
              </h3>
              <p class="text-white/60 leading-relaxed mb-10 text-lg font-light">
                Search meteorite data and interact with our AI-powered Q&A system. Explore our comprehensive database with advanced search capabilities and intelligent assistance.
              </p>
              
              <div class="flex items-center gap-4 text-starlight-blue font-semibold group-hover:translate-x-2 transition-transform duration-300">
                <span>Enter Workspace</span>
                <i class="bi bi-arrow-right text-xl"></i>
              </div>
            </div>
          </div>
        </AstroCard>
      </div>
    </div>
  </section>
</template>

<script setup>
import AstroCard from './ui/AstroCard.vue'

const navigateToWorkspace = () => {
  window.dispatchEvent(new CustomEvent('navigate-to-pdf', {
    detail: { page: 'workspace' }
  }));
};
</script>

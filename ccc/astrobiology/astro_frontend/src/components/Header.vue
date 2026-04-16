<template>
  <header 
    id="header" 
    class="fixed top-0 md:top-10 left-0 w-full z-50 transition-all duration-300 backdrop-blur-md border-b"
    :class="isScrolled ? 'border-glass-border shadow-lg !bg-space-black/60' : 'border-transparent !bg-space-black/20'"
  >
    <div class="container mx-auto px-6 h-20 flex items-center justify-between">
      <!-- Logo -->
      <a href="#" class="flex items-center gap-3 group" @click.prevent="scrollToTop">
        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-nebula-purple to-starlight-blue flex items-center justify-center shadow-[0_0_20px_rgba(108,92,231,0.5)] group-hover:scale-110 transition-transform duration-300">
          <i class="bi bi-stars text-white text-lg"></i>
        </div>
        <span class="text-2xl font-bold tracking-tight text-white group-hover:text-starlight-blue transition-colors">
          MustADB
        </span>
      </a>

      <!-- Desktop Navigation -->
      <nav class="hidden md:flex items-center gap-8">
        <a 
          v-for="item in navItems" 
          :key="item.id"
          :href="item.href"
          class="text-sm font-medium text-white/70 hover:text-white transition-colors relative py-2"
          :class="{ 'text-starlight-blue': activeSection === item.id }"
          @click.prevent="handleSmoothScroll(item.id)"
        >
          {{ item.label }}
          <span 
            class="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-starlight-blue transition-all duration-300"
            :class="{ 'w-full': activeSection === item.id }"
          ></span>
        </a>
      </nav>
      
      <!-- Mobile Menu Toggle -->
      <button class="md:hidden text-white/80 hover:text-white" @click="toggleMobileMenu">
        <i class="bi" :class="isMobileMenuOpen ? 'bi-x-lg' : 'bi-list'" style="font-size: 1.5rem;"></i>
      </button>
    </div>

    <!-- Mobile Menu -->
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="isMobileMenuOpen" class="md:hidden absolute top-full left-0 w-full bg-space-black/95 backdrop-blur-xl border-b border-glass-border">
        <div class="flex flex-col p-4 space-y-2">
          <a 
            v-for="item in navItems" 
            :key="item.id"
            :href="item.href"
            class="block px-4 py-3 rounded-lg text-white/80 hover:bg-white/5 hover:text-white transition-colors"
            :class="{ 'bg-white/10 text-starlight-blue': activeSection === item.id }"
            @click.prevent="handleSmoothScroll(item.id); isMobileMenuOpen = false"
          >
            {{ item.label }}
          </a>
        </div>
      </div>
    </transition>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const isScrolled = ref(false);
const isMobileMenuOpen = ref(false);
const activeSection = ref('hero');

const navItems = [
  { id: 'hero', label: 'Home', href: '#hero' },
  { id: 'workspace-entrance', label: 'Workspace', href: '#workspace-entrance' },
  { id: 'pdf-upload', label: 'Upload', href: '#pdf-upload' },
  { id: 'about', label: 'About', href: '#about' },
  { id: 'contact', label: 'Contact', href: '#contact' }
];

const handleScroll = () => {
  const currentScrollPos = window.scrollY;
  isScrolled.value = currentScrollPos > 50;
  
  // Update active section
  const sections = navItems.map(item => item.id);
  const headerHeight = window.innerWidth >= 768 ? 120 : 80; // Account for TopBar on desktop
  
  // If at the very top, always show Hero/Home as active
  if (currentScrollPos < 100) {
    activeSection.value = 'hero';
    return;
  }
  
  // Check each section
  for (const sectionId of sections) {
    const element = document.getElementById(sectionId);
    if (element) {
      const rect = element.getBoundingClientRect();
      const elementTop = rect.top;
      const elementBottom = rect.bottom;
      
      // Section is active if its top is near or above the header and bottom is below
      if (elementTop <= headerHeight + 50 && elementBottom >= headerHeight) {
        activeSection.value = sectionId;
        break;
      }
    }
  }
};

const handleSmoothScroll = (targetId) => {
  if (targetId === 'hero') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
  
  const element = document.getElementById(targetId);
  if (element) {
    const headerHeight = 80;
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerHeight;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });
  }
};

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value;
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll);
  handleScroll(); // Initial check
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<template>
  <canvas ref="canvas" class="star-field-canvas"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const canvas = ref(null)
let ctx = null
let animationFrameId = null
let stars = []
let nebulae = []
let width = 0
let height = 0
let mouse = { x: -1000, y: -1000 }

// Configuration
const STAR_COUNT = 200
const NEBULA_COUNT = 3
const MOUSE_RADIUS = 250

class Star {
  constructor() {
    this.reset(true)
  }

  reset(randomY = false) {
    this.x = Math.random() * width
    this.y = randomY ? Math.random() * height : height + 10
    this.vx = (Math.random() - 0.5) * 0.2
    this.vy = -(Math.random() * 0.3 + 0.1)
    this.size = Math.random() * 2 + 0.5
    this.alpha = Math.random() * 0.5 + 0.1
    this.baseAlpha = this.alpha
    this.twinkleSpeed = Math.random() * 0.02 + 0.01
    this.twinklePhase = Math.random() * Math.PI * 2
    
    const colors = ['255, 255, 255', '108, 92, 231', '0, 206, 201']
    this.color = colors[Math.floor(Math.random() * colors.length)]
  }

  update() {
    this.x += this.vx
    this.y += this.vy

    // Twinkling effect
    this.twinklePhase += this.twinkleSpeed
    this.alpha = this.baseAlpha + Math.sin(this.twinklePhase) * 0.2

    // Mouse interaction
    const dx = this.x - mouse.x
    const dy = this.y - mouse.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance < MOUSE_RADIUS) {
      const forceDirectionX = dx / distance
      const forceDirectionY = dy / distance
      const force = (MOUSE_RADIUS - distance) / MOUSE_RADIUS
      
      this.vx += forceDirectionX * force * 0.02
      this.vy += forceDirectionY * force * 0.02
      this.alpha = Math.min(this.baseAlpha + 0.4, 1)
    } else {
      if (this.alpha > this.baseAlpha + 0.2) {
        this.alpha -= 0.01
      }
    }

    if (this.vy > -0.1) this.vy -= 0.001
    
    if (this.y < -10 || this.x < -10 || this.x > width + 10) {
      this.reset()
    }
  }

  draw() {
    if (!ctx) return
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`
    ctx.fill()
  }
}

class Nebula {
  constructor() {
    this.x = Math.random() * width
    this.y = Math.random() * height
    this.radius = Math.random() * 200 + 150
    this.vx = (Math.random() - 0.5) * 0.1
    this.vy = (Math.random() - 0.5) * 0.1
    this.alpha = Math.random() * 0.05 + 0.02
    this.color = Math.random() > 0.5 ? '108, 92, 231' : '0, 206, 201'
  }

  update() {
    this.x += this.vx
    this.y += this.vy

    // Wrap around edges
    if (this.x < -this.radius) this.x = width + this.radius
    if (this.x > width + this.radius) this.x = -this.radius
    if (this.y < -this.radius) this.y = height + this.radius
    if (this.y > height + this.radius) this.y = -this.radius
  }

  draw() {
    if (!ctx) return
    const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius)
    gradient.addColorStop(0, `rgba(${this.color}, ${this.alpha})`)
    gradient.addColorStop(0.5, `rgba(${this.color}, ${this.alpha * 0.5})`)
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)')
    
    ctx.fillStyle = gradient
    ctx.fillRect(this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2)
  }
}

const init = () => {
  if (!canvas.value) return
  ctx = canvas.value.getContext('2d')
  resize()
  
  stars = []
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push(new Star())
  }

  nebulae = []
  for (let i = 0; i < NEBULA_COUNT; i++) {
    nebulae.push(new Nebula())
  }
  
  animate()
}

const resize = () => {
  if (!canvas.value) return
  width = window.innerWidth
  height = window.innerHeight
  canvas.value.width = width
  canvas.value.height = height
}

const animate = () => {
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  
  // Draw nebulae first (background layer)
  nebulae.forEach(nebula => {
    nebula.update()
    nebula.draw()
  })

  // Draw stars on top
  stars.forEach(star => {
    star.update()
    star.draw()
  })
  
  animationFrameId = requestAnimationFrame(animate)
}

const handleMouseMove = (e) => {
  mouse.x = e.clientX
  mouse.y = e.clientY
}

const handleResize = () => {
  resize()
}

onMounted(() => {
  init()
  window.addEventListener('resize', handleResize)
  window.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('mousemove', handleMouseMove)
})
</script>

<style scoped>
.star-field-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(circle at top left, #1a1c29 0%, #0B0D17 100%);
}
</style>

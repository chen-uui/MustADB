const fs = require('fs');
const path = require('path');

// 定义图标替换映射
const iconReplacements = {
  'Environment': 'Monitor',
  'TrendCharts': 'TrendCharts',
  'Moon': 'Moon',
  'Shield': 'Shield'
};

// 需要修复的文件列表
const filesToFix = [
  'src/components/OrganicCompoundsDisplay.vue',
  'src/components/ScientificInsightsDisplay.vue',
  'src/components/MineralRelationshipsDisplay.vue',
  'src/components/ValidationResultsDisplay.vue',
  'src/components/MeteoriteDataDisplay.vue'
];

function fixIconsInFile(filePath) {
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    let modified = false;
    
    // 替换导入中的图标
    Object.entries(iconReplacements).forEach(([oldIcon, newIcon]) => {
      if (content.includes(oldIcon)) {
        content = content.replace(new RegExp(`\\b${oldIcon}\\b`, 'g'), newIcon);
        modified = true;
      }
    });
    
    if (modified) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log(`Fixed icons in: ${filePath}`);
    } else {
      console.log(`No changes needed in: ${filePath}`);
    }
  } catch (error) {
    console.error(`Error fixing ${filePath}:`, error.message);
  }
}

// 修复所有文件
filesToFix.forEach(file => {
  const fullPath = path.join(__dirname, file);
  if (fs.existsSync(fullPath)) {
    fixIconsInFile(fullPath);
  } else {
    console.log(`File not found: ${fullPath}`);
  }
});

console.log('Icon fixing completed!');

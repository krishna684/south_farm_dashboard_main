// Placeholder image generator for testing
// This creates simple colored rectangles as placeholders

const canvas = document.createElement('canvas');
canvas.width = 400;
canvas.height = 300;
const ctx = canvas.getContext('2d');

// Function to create a placeholder image
function createPlaceholder(color, text) {
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 24px Arial';
  ctx.textAlign = 'center';
  ctx.fillText(text, canvas.width/2, canvas.height/2);
  
  return canvas.toDataURL('image/png');
}

// Generate placeholders
const redPlaceholder = createPlaceholder('#ff0000', 'Red Band Placeholder');
const greenPlaceholder = createPlaceholder('#00ff00', 'Green Band Placeholder');  
const bluePlaceholder = createPlaceholder('#0000ff', 'Blue Band Placeholder');

console.log('Red placeholder ready');
console.log('Green placeholder ready'); 
console.log('Blue placeholder ready');
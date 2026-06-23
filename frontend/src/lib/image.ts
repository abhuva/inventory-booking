const DEFAULT_SIZE = 768;
const DEFAULT_QUALITY = 0.72;

export async function prepareAssetImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/')) {
    throw new Error('Choose an image file.');
  }

  const bitmap = await createImageBitmap(file);
  try {
    const side = Math.min(bitmap.width, bitmap.height);
    const sourceX = Math.floor((bitmap.width - side) / 2);
    const sourceY = Math.floor((bitmap.height - side) / 2);
    const targetSize = Math.min(DEFAULT_SIZE, side);
    const canvas = document.createElement('canvas');
    canvas.width = targetSize;
    canvas.height = targetSize;
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Image processing is not available in this browser.');
    }
    context.drawImage(bitmap, sourceX, sourceY, side, side, 0, 0, targetSize, targetSize);

    const webpBlob = await canvasToBlob(canvas, 'image/webp', DEFAULT_QUALITY);
    if (webpBlob) {
      return new File([webpBlob], 'asset.webp', { type: 'image/webp' });
    }

    const jpegBlob = await canvasToBlob(canvas, 'image/jpeg', DEFAULT_QUALITY);
    if (!jpegBlob) {
      throw new Error('Could not process image.');
    }
    return new File([jpegBlob], 'asset.jpg', { type: 'image/jpeg' });
  } finally {
    bitmap.close();
  }
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
  mimeType: string,
  quality: number
): Promise<Blob | null> {
  return new Promise((resolve) => {
    canvas.toBlob(resolve, mimeType, quality);
  });
}

import QRCode from 'qrcode';

export async function renderQrSvg(value: string): Promise<string> {
  return await QRCode.toString(value, {
    type: 'svg',
    width: 320,
    margin: 2,
    errorCorrectionLevel: 'M'
  });
}

export function downloadSvg(filename: string, svg: string): void {
  const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function safeFilename(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

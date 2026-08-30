import QRCode from 'qrcode';
import type { Color, PDFFont, PDFImage, PDFPage } from 'pdf-lib';

const POINTS_PER_MM = 72 / 25.4;
const A4_WIDTH_MM = 210;
const A4_HEIGHT_MM = 297;
const PAGE_MARGIN_MM = 8;
const LABEL_GAP_MM = 2;
const LABEL_PADDING_MM = 2;
const LABEL_TEXT_HEIGHT_MM = 7.5;
const MIN_QR_SIZE_MM = 18;
const QR_QUIET_ZONE_MODULES = 4;
const QR_LOGO_URL = '/branding/nica-logo-black.png';

export const DEFAULT_QR_LOGO_RADIUS_PERCENT = 10;
export const MIN_QR_LOGO_RADIUS_PERCENT = 9;
export const VERIFIED_QR_LOGO_RADIUS_PERCENT = 16;
export const MAX_QR_LOGO_RADIUS_PERCENT = 20;
export const DEFAULT_QR_LOGO_SIZE_PERCENT = 20;
export const MIN_QR_LOGO_SIZE_PERCENT = 10;
export const MAX_QR_LOGO_SIZE_PERCENT = 40;

export interface QrPdfLabel {
  assetId: string;
  assetName: string;
  url: string;
}

export interface QrPdfGrid {
  columns: number;
  rows: number;
}

export interface QrPdfOptions {
  logoRadiusPercent?: number;
  logoSizePercent?: number;
}

export interface QrPdfLayout {
  pageWidth: number;
  pageHeight: number;
  margin: number;
  gap: number;
  cellWidth: number;
  cellHeight: number;
  labelPadding: number;
  textHeight: number;
  qrSize: number;
  qrSizeMm: number;
  labelsPerPage: number;
}

export function calculateQrPdfLayout(grid: QrPdfGrid): QrPdfLayout {
  if (!Number.isInteger(grid.columns) || grid.columns < 1 || grid.columns > 8) {
    throw new Error('Columns must be a whole number from 1 to 8.');
  }
  if (!Number.isInteger(grid.rows) || grid.rows < 1 || grid.rows > 8) {
    throw new Error('Rows must be a whole number from 1 to 8.');
  }

  const pageWidth = mmToPoints(A4_WIDTH_MM);
  const pageHeight = mmToPoints(A4_HEIGHT_MM);
  const margin = mmToPoints(PAGE_MARGIN_MM);
  const gap = mmToPoints(LABEL_GAP_MM);
  const labelPadding = mmToPoints(LABEL_PADDING_MM);
  const textHeight = mmToPoints(LABEL_TEXT_HEIGHT_MM);
  const cellWidth = (pageWidth - margin * 2 - gap * (grid.columns - 1)) / grid.columns;
  const cellHeight = (pageHeight - margin * 2 - gap * (grid.rows - 1)) / grid.rows;
  const qrSize = Math.min(cellWidth - labelPadding * 2, cellHeight - labelPadding * 2 - textHeight);
  const qrSizeMm = pointsToMm(qrSize);

  if (qrSizeMm < MIN_QR_SIZE_MM) {
    throw new Error(
      `This grid leaves only ${qrSizeMm.toFixed(1)} mm for each QR code. Use fewer rows or columns.`
    );
  }

  return {
    pageWidth,
    pageHeight,
    margin,
    gap,
    cellWidth,
    cellHeight,
    labelPadding,
    textHeight,
    qrSize,
    qrSizeMm,
    labelsPerPage: grid.columns * grid.rows
  };
}

export async function createQrLabelPdf(
  labels: QrPdfLabel[],
  grid: QrPdfGrid,
  options: QrPdfOptions = {}
): Promise<Uint8Array> {
  if (!labels.length) {
    throw new Error('Choose at least one QR label.');
  }

  const layout = calculateQrPdfLayout(grid);
  const logoRadiusPercent = options.logoRadiusPercent ?? DEFAULT_QR_LOGO_RADIUS_PERCENT;
  const logoSizePercent = options.logoSizePercent ?? DEFAULT_QR_LOGO_SIZE_PERCENT;
  if (
    !Number.isFinite(logoRadiusPercent) ||
    logoRadiusPercent < MIN_QR_LOGO_RADIUS_PERCENT ||
    logoRadiusPercent > MAX_QR_LOGO_RADIUS_PERCENT
  ) {
    throw new Error(
      `Logo radius must be from ${MIN_QR_LOGO_RADIUS_PERCENT}% to ${MAX_QR_LOGO_RADIUS_PERCENT}%.`
    );
  }
  if (
    !Number.isFinite(logoSizePercent) ||
    logoSizePercent < MIN_QR_LOGO_SIZE_PERCENT ||
    logoSizePercent > MAX_QR_LOGO_SIZE_PERCENT
  ) {
    throw new Error(
      `Logo size must be from ${MIN_QR_LOGO_SIZE_PERCENT}% to ${MAX_QR_LOGO_SIZE_PERCENT}%.`
    );
  }

  const { PDFDocument, StandardFonts, grayscale } = await import('pdf-lib');
  const pdf = await PDFDocument.create();
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const logo = await pdf.embedPng(await loadQrLogo());
  const white = grayscale(1);
  pdf.setTitle('Inventory QR labels');
  pdf.setSubject('Printable A4 inventory QR label sheet');
  pdf.setCreator('NICA Inventory Booking');

  for (let pageOffset = 0; pageOffset < labels.length; pageOffset += layout.labelsPerPage) {
    const page = pdf.addPage([layout.pageWidth, layout.pageHeight]);
    const pageLabels = labels.slice(pageOffset, pageOffset + layout.labelsPerPage);
    pageLabels.forEach((label, index) => {
      const column = index % grid.columns;
      const row = Math.floor(index / grid.columns);
      const cellX = layout.margin + column * (layout.cellWidth + layout.gap);
      const cellY =
        layout.pageHeight -
        layout.margin -
        layout.cellHeight -
        row * (layout.cellHeight + layout.gap);

      page.drawRectangle({
        x: cellX,
        y: cellY,
        width: layout.cellWidth,
        height: layout.cellHeight,
        borderColor: grayscale(0.72),
        borderWidth: 0.4
      });
      drawQrCode(
        page,
        label.url,
        cellX,
        cellY,
        layout,
        logo,
        white,
        logoRadiusPercent,
        logoSizePercent
      );
      drawAssetName(page, font, label.assetName, cellX, cellY, layout);
    });
  }

  return await pdf.save();
}

export function downloadQrLabelPdf(bytes: Uint8Array): void {
  const blob = new Blob([new Uint8Array(bytes)], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `inventory-qr-labels-${new Date().toISOString().slice(0, 10)}.pdf`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function drawQrCode(
  page: PDFPage,
  url: string,
  cellX: number,
  cellY: number,
  layout: QrPdfLayout,
  logo: PDFImage,
  white: Color,
  logoRadiusPercent: number,
  logoSizePercent: number
): void {
  const qrCode = QRCode.create(url, { errorCorrectionLevel: 'H' });
  const totalModules = qrCode.modules.size + QR_QUIET_ZONE_MODULES * 2;
  const moduleSize = layout.qrSize / totalModules;
  const qrX = cellX + (layout.cellWidth - layout.qrSize) / 2;
  const qrRegionHeight = layout.cellHeight - layout.labelPadding * 2 - layout.textHeight;
  const qrY =
    cellY + layout.labelPadding + layout.textHeight + (qrRegionHeight - layout.qrSize) / 2;

  for (let row = 0; row < qrCode.modules.size; row += 1) {
    let runStart = -1;
    for (let column = 0; column <= qrCode.modules.size; column += 1) {
      const dark = column < qrCode.modules.size && qrCode.modules.get(row, column) === 1;
      if (dark && runStart === -1) {
        runStart = column;
      }
      if (!dark && runStart !== -1) {
        page.drawRectangle({
          x: qrX + (runStart + QR_QUIET_ZONE_MODULES) * moduleSize,
          y: qrY + (QR_QUIET_ZONE_MODULES + qrCode.modules.size - row - 1) * moduleSize,
          width: (column - runStart) * moduleSize,
          height: moduleSize
        });
        runStart = -1;
      }
    }
  }

  const centerX = qrX + layout.qrSize / 2;
  const centerY = qrY + layout.qrSize / 2;
  const backdropRadius = layout.qrSize * (logoRadiusPercent / 100);
  const logoSize = layout.qrSize * (logoSizePercent / 100);
  page.drawCircle({
    x: centerX,
    y: centerY,
    size: backdropRadius,
    color: white
  });
  page.drawImage(logo, {
    x: centerX - logoSize / 2,
    y: centerY - logoSize / 2,
    width: logoSize,
    height: logoSize
  });
}

async function loadQrLogo(): Promise<Uint8Array> {
  const response = await fetch(QR_LOGO_URL);
  if (!response.ok) {
    throw new Error('Could not load the NICA logo for the PDF.');
  }
  return new Uint8Array(await response.arrayBuffer());
}

function drawAssetName(
  page: PDFPage,
  font: PDFFont,
  assetName: string,
  cellX: number,
  cellY: number,
  layout: QrPdfLayout
): void {
  const maxWidth = layout.cellWidth - layout.labelPadding * 2;
  const { text, size } = fitText(font, printableText(assetName), maxWidth);
  const textWidth = font.widthOfTextAtSize(text, size);
  const textHeight = font.heightAtSize(size);
  page.drawText(text, {
    x: cellX + (layout.cellWidth - textWidth) / 2,
    y: cellY + layout.labelPadding + (layout.textHeight - textHeight) / 2,
    size,
    font
  });
}

function fitText(font: PDFFont, value: string, maxWidth: number): { text: string; size: number } {
  const normalized = value.trim().replace(/\s+/g, ' ') || 'Unnamed asset';
  for (let size = 10; size >= 6; size -= 0.5) {
    if (font.widthOfTextAtSize(normalized, size) <= maxWidth) {
      return { text: normalized, size };
    }
  }

  let shortened = normalized;
  while (shortened.length > 1 && font.widthOfTextAtSize(`${shortened}...`, 6) > maxWidth) {
    shortened = shortened.slice(0, -1);
  }
  return { text: `${shortened.trimEnd()}...`, size: 6 };
}

function printableText(value: string): string {
  return Array.from(value, (character) => {
    const codePoint = character.codePointAt(0) ?? 0;
    return codePoint <= 255 ? character : '?';
  }).join('');
}

function mmToPoints(value: number): number {
  return value * POINTS_PER_MM;
}

function pointsToMm(value: number): number {
  return value / POINTS_PER_MM;
}

import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspace = path.resolve(".");
const coverDir = path.resolve(workspace, "..", "..", "cover");
const backgroundPath = path.join(coverDir, "cover-background-editable-v1.png");
const outputPptx = path.join(coverDir, "cover-canva-editable-v1.pptx");
const outputPreview = path.join(coverDir, "cover-canva-editable-preview-v1.png");
const outputLayout = path.join(workspace, "cover-canva-editable-v1.layout.json");

async function writeBlob(outputPath, blob) {
  await fs.writeFile(outputPath, new Uint8Array(await blob.arrayBuffer()));
}

function addText(slide, {
  name,
  text,
  left,
  top,
  width,
  height,
  fontSize,
  color,
  alignment = "center",
  verticalAlignment = "middle",
  bold = true,
}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    name,
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    typeface: "Noto Sans JP",
    fontSize,
    bold,
    color,
    alignment,
    verticalAlignment,
    autoFit: "shrinkText",
    wrap: "square",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return box;
}

async function main() {
  const presentation = Presentation.create({
    slideSize: { width: 1024, height: 1536 },
  });
  const slide = presentation.slides.add();

  const backgroundBytes = await fs.readFile(backgroundPath);
  slide.images.add({
    blob: backgroundBytes,
    contentType: "image/png",
    alt: "分離と再結合を表す、文字なしのソフトウェア設計イラスト",
    name: "背景イラスト（差し替え可能）",
    fit: "cover",
    position: { left: 0, top: 0, width: 1024, height: 1536 },
  });

  addText(slide, {
    name: "タイトル1",
    text: "デザインパターンで学ぶ",
    left: 58,
    top: 43,
    width: 908,
    height: 104,
    fontSize: 70,
    color: "#050505",
  });

  addText(slide, {
    name: "タイトル2",
    text: "C++ソフトウェア設計",
    left: 58,
    top: 151,
    width: 908,
    height: 118,
    fontSize: 82,
    color: "#050505",
  });

  slide.shapes.add({
    geometry: "rect",
    name: "タイトル下罫線",
    position: { left: 60, top: 286, width: 904, height: 5 },
    fill: "#123F91",
    line: { style: "solid", fill: "#123F91", width: 0 },
  });

  addText(slide, {
    name: "サブタイトル",
    text: "分離と再結合で、設計を決める思考プロセス",
    left: 76,
    top: 306,
    width: 872,
    height: 52,
    fontSize: 30,
    color: "#111827",
  });

  addText(slide, {
    name: "帯見出し",
    text: "パターンを当てはめる前に、\n設計すべき構造を見つける。",
    left: 58,
    top: 1256,
    width: 908,
    height: 94,
    fontSize: 38,
    color: "#FFFFFF",
    alignment: "left",
  });

  addText(slide, {
    name: "帯説明",
    text: "現状を捉え、結合部分の課題を見つけ、責任を分離し、\n動くシステムとして再結合する。",
    left: 58,
    top: 1362,
    width: 908,
    height: 76,
    fontSize: 27,
    color: "#FFFFFF",
    alignment: "left",
  });

  addText(slide, {
    name: "帯結論",
    text: "型ではなく、デザインパターンに至る考え方を学ぶ。",
    left: 58,
    top: 1454,
    width: 908,
    height: 42,
    fontSize: 25,
    color: "#FFE38A",
    alignment: "left",
  });

  const preview = await presentation.export({
    slide,
    format: "png",
    scale: 1,
  });
  await writeBlob(outputPreview, preview);

  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(outputLayout, await layout.text(), "utf8");

  const inspection = await presentation.inspect({
    kind: "slide,shape,textbox,image",
    maxChars: 12000,
  });
  await fs.writeFile(
    path.join(workspace, "cover-canva-editable-v1.inspect.json"),
    typeof inspection === "string" ? inspection : JSON.stringify(inspection, null, 2),
    "utf8",
  );

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPptx);

  console.log(JSON.stringify({ outputPptx, outputPreview, outputLayout }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

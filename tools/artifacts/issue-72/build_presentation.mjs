import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const ROOT = process.env.TECHFLOW_ROOT;
if (!ROOT) throw new Error("TECHFLOW_ROOT is required");
const renderDir = path.join(ROOT, "tmp", "issue72-presentation", "renders");
const output = path.join(ROOT, "output", "presentation", "techflow-issue-72-large-upload.pptx");
await fs.mkdir(renderDir, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { ink: "#101010", gray: "#5B616B", panel: "#EDEDED", rule: "#B8BCC4", pale: "#EAF5FB", blue: "#3D8DFF", green: "#117A4B", white: "#FFFFFF" };
const FONT = "Malgun Gothic";

function box(slide, name, left, top, width, height, fill=C.white, line=C.rule) {
  return slide.shapes.add({ geometry: "rect", name, position: { left, top, width, height }, fill, line: { style: "solid", fill: line, width: 1 } });
}
function text(slide, name, value, left, top, width, height, size=24, bold=false, color=C.ink, align="left") {
  const item=slide.shapes.add({ geometry:"textbox", name, position:{left,top,width,height}, fill:"none", line:{style:"solid",fill:"none",width:0} });
  item.text=value; item.text.style={fontSize:size,bold,color,typeface:FONT,alignment:align}; return item;
}
function title(slide, value, number) {
  text(slide, `title-${number}`, value, 42, 34, 1120, 88, 46, true);
  text(slide, `page-${number}`, String(number).padStart(2,"0"), 1180, 656, 58, 24, 16, false, C.gray, "right");
}
function notes(slide) {
  slide.speakerNotes.textFrame.setText("[Sources]\n- docs/evidence/issue-72/large-upload-production-validation.json\n- docs/reports/issue-72-community-large-upload-validation.md\n- docs/runbooks/community-large-uploads.md");
}

{
  const s=deck.slides.add(); s.background.fill=C.white;
  text(s,"cover-kicker","ABLESTACK TECHFLOW · ISSUE #72",42,42,560,42,20,true,C.gray);
  text(s,"cover-title","Community 대용량\n첨부 개선 완료",42,190,560,190,66,true);
  text(s,"cover-subtitle","실파일 경계 · 디스크 스트리밍 · 운영 검증",42,430,560,70,28,false,C.gray);
  box(s,"cover-hero",660,42,578,588,C.pale,C.rule);
  text(s,"cover-stat","1 / 10\nGiB",708,160,480,240,84,true,C.blue,"center");
  text(s,"cover-detail","일반 / 압축 파일 상한\n2026.08.16",708,430,480,100,26,false,C.gray,"center");
  notes(s);
}
{
  const s=deck.slides.add(); title(s,"1 GiB / 10 GiB 정책이 전 계층을 관통합니다",2);
  const labels=["Nginx\n11 GiB","PHP-FPM\n10 / 11 GiB","Flarum\n1 / 10 GiB","Poller\n디스크 저장","Gateway\n스트리밍","압축 해제\n100 GiB"];
  labels.forEach((label,i)=>{ const left=42+i*199; box(s,`flow-${i}`,left,260,164,150,i===2||i===4?C.pale:C.panel,i===2||i===4?C.blue:C.rule); text(s,`flow-text-${i}`,label,left+12,300,140,70,24,true,C.ink,"center"); if(i<5) text(s,`arrow-${i}`,"→",left+166,313,34,40,30,true,C.gray,"center"); });
  text(s,"flow-foot","7,200초 · 2회 재시도 · 100개 항목 · 압축비 20배 · AI에는 정규화 근거만 전달",42,500,1196,62,24,false,C.gray,"center"); notes(s);
}
{
  const s=deck.slides.add(); title(s,"수신·분석 경계를 함께 확장했습니다",3);
  const values=[["계층","적용 전","적용 후"],["Nginx","120 MiB","11 GiB · 7,200초"],["PHP-FPM","120 / 120 MiB","파일 10 / 요청 11 GiB"],["Flarum","50 MiB","일반 1 / 압축 10 GiB"],["Poller","50 MiB · 120초","1 / 10 GiB · 7,200초"],["Gateway","원본 50 / 해제 100 MiB","원본 1/10 · 해제 100 GiB"]];
  const t=s.tables.add({rows:6,columns:3,left:42,top:170,width:1196,height:430,columnWidths:[250,430,516],values});
  t.borders.assign({style:"solid",fill:C.rule,width:1});
  for(let c=0;c<3;c++){t.getCell(0,c).fill="#243B64"; t.getCell(0,c).text.style={fontSize:22,bold:true,color:C.white,typeface:FONT};}
  for(let r=1;r<6;r++) for(let c=0;c<3;c++){t.getCell(r,c).fill=r%2?C.white:"#F7F9FC";t.getCell(r,c).text.style={fontSize:19,bold:c===0,color:C.ink,typeface:FONT};}
  notes(s);
}
{
  const s=deck.slides.add(); title(s,"정확한 경계 크기로 운영 경로를 검증했습니다",4);
  const cards=[{v:"263/263",d:"전체 런타임 회귀"},{v:"1 / 10 GiB",d:"허용 · +1 byte 거부"},{v:"60.3 MiB",d:"10 GiB 분석 최대 메모리"}];
  cards.forEach((card,i)=>{const left=42+i*411;box(s,`metric-${i}`,left,300,374,270,C.panel,C.panel);text(s,`metric-value-${i}`,card.v,left+28,350,318,100,56,true,i===1?C.blue:C.ink,"center");text(s,`metric-detail-${i}`,card.d,left+28,478,318,46,23,false,C.gray,"center");});
  text(s,"metric-caption","Flarum 1 GiB 16초 · 10 GiB 410초 | Gateway 1 GiB 27.751초 · 10 GiB 294.814초",42,160,1196,72,25,false,C.gray,"center"); notes(s);
}
{
  const s=deck.slides.add(); title(s,"위험한 압축과 위장 파일은 모두 닫힌 상태로 거부됩니다",5);
  const values=[["시험","HTTP","판정"],["경로 이탈 ZIP","400","거부"],["중첩 압축","400","거부"],["압축 폭탄","400","거부"],["실행 파일 포함","400","거부"],["PNG MIME 위장","400","거부"]];
  const t=s.tables.add({rows:6,columns:3,left:42,top:176,width:760,height:420,columnWidths:[450,130,180],values}); t.borders.assign({style:"solid",fill:C.rule,width:1});
  for(let c=0;c<3;c++){t.getCell(0,c).fill="#243B64";t.getCell(0,c).text.style={fontSize:22,bold:true,color:C.white,typeface:FONT};}
  for(let r=1;r<6;r++)for(let c=0;c<3;c++){t.getCell(r,c).fill=r%2?C.white:"#F7F9FC";t.getCell(r,c).text.style={fontSize:20,bold:c===2,color:c===2?C.green:C.ink,typeface:FONT};}
  box(s,"security-side",850,176,388,420,C.pale,C.blue); text(s,"security-side-title","검증 후 정리",884,220,320,45,28,true,C.blue);
  text(s,"security-side-body","Flarum 첨부 2건 삭제\nGateway Artifact 2건 삭제\n시험 컨테이너 6개 삭제\n시험 볼륨 7개 삭제\n\nDB·파일 잔존\n0건",884,292,320,250,24,false,C.ink); notes(s);
}
{
  const s=deck.slides.add(); s.background.fill=C.white;
  text(s,"close-kicker","ISSUE #72 · COMPLETE",42,42,420,42,20,true,C.gray);
  text(s,"close-title","운영 상태는\nGO입니다",42,188,850,190,82,true);
  text(s,"close-detail","Gateway healthy · Poller failed=0 · Maintainer level=ok\nGitHub→Chat 보호 서비스 frozen / guard passed",42,485,800,85,28,false,C.gray);
  box(s,"close-badge",934,208,304,304,C.pale,C.blue); text(s,"close-go","GO",964,296,244,100,72,true,C.blue,"center");
  notes(s);
}

for (const [index,slide] of deck.slides.items.entries()) {
  const blob=await deck.export({slide,format:"png",scale:1});
  await fs.writeFile(path.join(renderDir,`slide-${String(index+1).padStart(2,"0")}.png`),new Uint8Array(await blob.arrayBuffer()));
  const layout=await slide.export({format:"layout"}); await fs.writeFile(path.join(renderDir,`slide-${String(index+1).padStart(2,"0")}.layout.json`),await layout.text());
}
const pptx=await PresentationFile.exportPptx(deck); await pptx.save(output); console.log(output);

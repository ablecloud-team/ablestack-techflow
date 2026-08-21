import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const runtimeModules = process.env.RUNTIME_NODE_MODULES;
const ROOT = process.env.TECHFLOW_ROOT;
if (!runtimeModules || !ROOT) throw new Error("RUNTIME_NODE_MODULES and TECHFLOW_ROOT are required");
const artifactToolUrl = pathToFileURL(path.join(runtimeModules, "@oai", "artifact-tool", "dist", "artifact_tool.mjs")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);
const renderDir = path.join(ROOT, "tmp", "epic70-presentation", "renders");
const output = path.join(ROOT, "output", "presentation", "techflow-community-modernization.pptx");
const screenshot = path.join(ROOT, "docs", "evidence", "epic-70", "community-discussion-174.jpg");
await fs.mkdir(renderDir, { recursive: true }); await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { ink:"#15253E", gray:"#52647D", canvas:"#F3F7FC", line:"#D5E1F1", pale:"#EAF2FF", blue:"#155EEF", cyan:"#25B8E8", green:"#078248", paleGreen:"#EAFAF2", white:"#FFFFFF", dark:"#243B64", amber:"#9A6700" };
const FONT = "Malgun Gothic";
function box(s,n,l,t,w,h,f=C.white,ln=C.line,g="roundRect"){ return s.shapes.add({geometry:g,name:n,position:{left:l,top:t,width:w,height:h},fill:f,line:{style:"solid",fill:ln,width:1},borderRadius:"rounded-xl"}); }
function text(s,n,v,l,t,w,h,z=24,b=false,c=C.ink,a="left"){ const x=s.shapes.add({geometry:"textbox",name:n,position:{left:l,top:t,width:w,height:h},fill:"none",line:{style:"solid",fill:"none",width:0}}); x.text=v; x.text.style={fontSize:z,bold:b,color:c,typeface:FONT,alignment:a}; return x; }
function title(s,v,n){ text(s,`title-${n}`,v,48,36,1110,72,40,true); text(s,`page-${n}`,String(n).padStart(2,"0"),1172,660,60,24,16,false,C.gray,"right"); }
function notes(s){ s.speakerNotes.textFrame.setText("[Sources]\n- docs/reports/epic-70-community-modernization-validation.md\n- docs/evidence/epic-70/community-modernization-e2e.json\n- docs/runbooks/community-platform-integrated-e2e.md\n- https://community.ablecloud.io/d/174"); }
function metric(s,n,v,label,l,t,w,color=C.blue){ box(s,`${n}-box`,l,t,w,178,C.white,C.line); box(s,`${n}-rule`,l,t,8,178,color,color,"rect"); text(s,`${n}-value`,v,l+24,t+32,w-48,64,44,true,color,"center"); text(s,`${n}-label`,label,l+24,t+112,w-48,40,20,false,C.gray,"center"); }
const screenshotBytes = await fs.readFile(screenshot); const screenshotBlob=screenshotBytes.buffer.slice(screenshotBytes.byteOffset,screenshotBytes.byteOffset+screenshotBytes.byteLength);

{
 const s=deck.slides.add(); s.background.fill=C.white;
 text(s,"cover-kicker","ABLESTACK TECHFLOW · EPIC #70",48,42,620,34,20,true,C.gray);
 text(s,"cover-title","Community 지원 흐름을\n운영 가능한 제품으로",48,145,700,190,62,true);
 text(s,"cover-sub","업데이트 · 대용량 첨부 · 현대화 UI · 복구 가능한 운영",48,380,730,64,26,false,C.gray);
 box(s,"cover-go",860,132,330,330,C.pale,C.blue); text(s,"cover-go-text","GO",890,218,270,92,72,true,C.blue,"center"); text(s,"cover-proof","Issue #71~#74\n통합 E2E 통과",900,328,250,88,24,true,C.ink,"center");
 text(s,"cover-date","2026.08.21 · Production validated",48,590,650,38,20,false,C.gray); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"질문이 해결 지식으로 이어지는 한 흐름을 완성했습니다",2);
 const steps=[["01","질문·첨부"],["02","AI 분석"],["03","친절한 답변"],["04","후속 대화"],["05","해결 선택"],["06","KB 최종본"]];
 steps.forEach((x,i)=>{ const l=44+i*204; if(i<5) text(s,`arrow-${i}`,"→",l+164,303,40,44,28,true,C.gray,"center"); box(s,`step-${i}`,l,222,164,214,i===5?C.paleGreen:C.canvas,i===5?C.green:C.line); text(s,`no-${i}`,x[0],l+18,247,128,32,17,true,i===5?C.green:C.gray,"center"); text(s,`label-${i}`,x[1],l+14,308,136,60,22,true,C.ink,"center"); });
 text(s,"flow-foot","Chat은 신규·후속·KB 완료와 장애·복구 전이에만 알립니다",80,530,1120,52,25,true,C.blue,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"Discussion #174에서 전체 E2E가 실제로 통과했습니다",3);
 s.images.add({name:"discussion-174",blob:screenshotBlob,contentType:"image/jpeg",fit:"contain",position:{left:48,top:132,width:690,height:440},geometry:"roundRect",borderRadius:"rounded-xl"});
 box(s,"timeline",780,132,440,440,C.canvas,C.line);
 const rows=[["#404","이미지·로그 질문"],["#405","첫 답변 + Chat"],["#406","후속 질문"],["#407","맥락 답변 + Chat"],["#408","KB + Best Answer"]];
 rows.forEach((r,i)=>{ const y=166+i*74; text(s,`post-${i}`,r[0],812,y,74,34,20,true,i===4?C.green:C.blue); text(s,`post-label-${i}`,r[1],898,y,282,34,20,i===4,C.ink); if(i<4) box(s,`post-line-${i}`,842,y+40,2,28,C.line,C.line,"rect"); });
 text(s,"case","같은 Case · contextVersion 5",790,540,420,34,20,true,C.green,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"제품 우선 증거를 쓰되 사용자는 필요한 답만 봅니다",4);
 const sources=[["1","ABLESTACK 문서"],["2","Cloud Diplo"],["3","연관 제품 코드"],["4","Europa Preview"],["5","libvirt·QEMU 공식 자료"]];
 sources.forEach((r,i)=>{ const y=144+i*84; box(s,`source-${i}`,62,y,500,62,i<3?C.pale:C.canvas,i<3?C.blue:C.line); text(s,`source-no-${i}`,r[0],82,y+15,40,30,18,true,C.blue,"center"); text(s,`source-name-${i}`,r[1],138,y+15,390,30,21,true,C.ink); });
 box(s,"user-output",640,144,570,398,C.paleGreen,"#86D2AA"); text(s,"user-head","사용자에게 보이는 답변",680,184,490,44,28,true,C.green,"center");
 text(s,"user-copy","친절한 전문 엔지니어 문장\n현재 원인과 조치 순서\n실행 전·중·후 CLI 확인\n필요한 추가 자료 요청\n\n내부 경로·Commit·Citation은 숨김",690,258,470,224,24,false,C.ink,"center");
 text(s,"kb","KB: 증상 · 원인 · 해결 방법 · 추가 고려사항 · 적용 버전",100,594,1080,40,23,true,C.blue,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"복구·관측·보안과 보호 서비스 불변성을 함께 확인했습니다",5);
 metric(s,"tests","175","Repository tests",52,148,260,C.blue); metric(s,"restore","11초","WSL 전체 복원",354,148,260,C.green); metric(s,"files","11,336","복원 File",656,148,260,C.cyan); metric(s,"alerts","0","정상 주기 알림",958,148,260,C.green);
 const checks=[["서비스","3/3 active"],["HTTP","200/200/200"],["Backup","integrity true"],["Security","Header 5 · WW 0"]];
 checks.forEach((r,i)=>{ const l=66+i*292; box(s,`check-${i}`,l,392,248,92,C.canvas,C.line); text(s,`check-title-${i}`,r[0],l+20,410,208,28,19,true,C.gray,"center"); text(s,`check-value-${i}`,r[1],l+20,448,208,28,20,true,C.ink,"center"); });
 text(s,"guard","GitHub→Chat Guard passed / passed · Container ID·Image·StartedAt 동일",80,560,1120,48,24,true,C.green,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white;
 text(s,"close-kicker","EPIC #70 · COMPLETE",48,42,540,34,20,true,C.gray);
 text(s,"close-title","Community 현대화는\nGO입니다",48,150,690,180,64,true);
 text(s,"close-copy","Issue #71~#74 완료\n운영 통합 E2E 완료\nMD · PDF · PPTX/PDF 자산화 완료",48,390,650,130,27,false,C.gray);
 box(s,"close-status",860,166,330,310,C.pale,C.blue); text(s,"close-go","GO",900,234,250,88,70,true,C.blue,"center"); text(s,"close-data","질문 → KB\n하나의 운영 흐름",900,344,250,82,23,true,C.ink,"center");
 text(s,"close-next","다음: Draft PR #65 최신 main 정합성·품질·통합 결과 최종 검토",48,582,1130,48,24,true,C.green); notes(s);
}

for (const [index,slide] of deck.slides.items.entries()) { const stem=`slide-${String(index+1).padStart(2,"0")}`; const png=await deck.export({slide,format:"png",scale:1}); await fs.writeFile(path.join(renderDir,`${stem}.png`),new Uint8Array(await png.arrayBuffer())); const layout=await slide.export({format:"layout"}); await fs.writeFile(path.join(renderDir,`${stem}.layout.json`),await layout.text()); }
const montage=await deck.export({format:"webp",montage:true,scale:1}); await fs.writeFile(path.join(renderDir,"montage.webp"),new Uint8Array(await montage.arrayBuffer()));
const pptx=await PresentationFile.exportPptx(deck); await pptx.save(output); console.log(output);

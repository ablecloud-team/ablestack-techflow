import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const runtimeModules = process.env.RUNTIME_NODE_MODULES;
const ROOT = process.env.TECHFLOW_ROOT;
if (!runtimeModules || !ROOT) throw new Error("RUNTIME_NODE_MODULES and TECHFLOW_ROOT are required");
const artifactToolUrl = pathToFileURL(path.join(runtimeModules, "@oai", "artifact-tool", "dist", "artifact_tool.mjs")).href;
const { Presentation, PresentationFile } = await import(artifactToolUrl);
const data = JSON.parse(await fs.readFile(path.join(ROOT, "docs", "evidence", "epic-4", "production-e2e.json"), "utf8"));
const renderDir = path.join(ROOT, "tmp", "epic4-presentation", "renders");
const output = path.join(ROOT, "output", "presentation", "techflow-epic4-assist-validation.pptx");
await fs.mkdir(renderDir, { recursive: true }); await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C = { ink:"#15253E", gray:"#52647D", canvas:"#F3F7FC", line:"#D5E1F1", pale:"#EAF2FF", blue:"#155EEF", cyan:"#25B8E8", green:"#078248", paleGreen:"#EAFAF2", white:"#FFFFFF", dark:"#243B64" };
const FONT = "Malgun Gothic";
function box(s,n,l,t,w,h,f=C.white,ln=C.line,g="roundRect"){ return s.shapes.add({geometry:g,name:n,position:{left:l,top:t,width:w,height:h},fill:f,line:{style:"solid",fill:ln,width:1},borderRadius:"rounded-xl"}); }
function txt(s,n,v,l,t,w,h,z=24,b=false,c=C.ink,a="left"){ const x=s.shapes.add({geometry:"textbox",name:n,position:{left:l,top:t,width:w,height:h},fill:"none",line:{style:"solid",fill:"none",width:0}}); x.text=v; x.text.style={fontSize:z,bold:b,color:c,typeface:FONT,alignment:a}; return x; }
function title(s,v,n){ txt(s,`title-${n}`,v,48,36,1120,72,40,true); txt(s,`page-${n}`,String(n).padStart(2,"0"),1172,660,60,24,16,false,C.gray,"right"); }
function notes(s){ s.speakerNotes.textFrame.setText("[Sources]\n- docs/reports/epic4-assist-validation.md\n- docs/evidence/epic-4/production-e2e.json\n- docs/runbooks/epic4-service-continuity.md\n- docs/plans/epic5-assist-mvp-plan.md"); }
function metric(s,n,v,label,l,t,w,color=C.blue){ box(s,`${n}-box`,l,t,w,178,C.white,C.line); box(s,`${n}-rule`,l,t,8,178,color,color,"rect"); txt(s,`${n}-value`,v,l+24,t+32,w-48,64,44,true,color,"center"); txt(s,`${n}-label`,label,l+24,t+112,w-48,40,20,false,C.gray,"center"); }

{
 const s=deck.slides.add(); s.background.fill=C.white;
 txt(s,"cover-kicker","ABLESTACK TECHFLOW · EPIC #4",48,42,620,34,20,true,C.gray);
 txt(s,"cover-title","Chat·Community Assist\n운영 실증 완료",48,145,700,190,62,true);
 txt(s,"cover-sub","연속 대화 · 자동 게시 · 실패 복구 · 비식별 KPI",48,380,730,64,26,false,C.gray);
 box(s,"cover-go",860,132,330,330,C.pale,C.blue); txt(s,"cover-go-text","GO",890,218,270,92,72,true,C.blue,"center"); txt(s,"cover-proof","271 tests\n운영 E2E 통과",900,328,250,88,24,true,C.ink,"center");
 txt(s,"cover-date","2026.08.21 · Production validated",48,590,650,38,20,false,C.gray); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"두 채널이 하나의 지원 원칙으로 작동합니다",2);
 const channels=[["Community","새 글·후속 글·해결·KB"],["Chat","직접 질문·맥락·해결"]];
 channels.forEach((r,i)=>{ const l=60+i*310; box(s,`channel-${i}`,l,158,260,176,i?C.paleGreen:C.pale,i?C.green:C.blue); txt(s,`channel-title-${i}`,r[0],l+20,190,220,40,28,true,i?C.green:C.blue,"center"); txt(s,`channel-copy-${i}`,r[1],l+24,254,212,46,18,false,C.ink,"center"); });
 txt(s,"arrow","→",674,220,58,50,38,true,C.gray,"center"); box(s,"gateway",748,130,470,260,C.canvas,C.line); txt(s,"gateway-title","Assist Gateway",788,168,390,44,30,true,C.ink,"center");
 txt(s,"gateway-copy","DOC · Diplo · 관련 코드\nEuropa Preview · Artifact\nConversation · KB · KPI",798,236,370,116,22,false,C.gray,"center");
 txt(s,"principle","사용자는 친절한 답만 보고, 내부 근거는 명시 요청 때만 봅니다",100,526,1080,50,25,true,C.blue,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"실제 Chat과 Community 경로를 끝까지 검증했습니다",3);
 metric(s,"chat1",String(data.chatE2E.firstAnswerLength),"첫 Chat 답변 글자",52,146,260,C.blue);
 metric(s,"chat2",String(data.chatE2E.secondAnswerLength),"후속 Chat 답변 글자",354,146,260,C.cyan);
 metric(s,"community",String(data.communityE2E.publishedContentLength),"Community 게시 글자",656,146,260,C.green);
 metric(s,"tests",String(data.localValidation.testsPassed),"Repository tests",958,146,260,C.blue);
 const flow=[["질문 1","Context 시작"],["질문 2","앞 질문 유지"],["해결","RESOLVED"],["Discussion #175","Post #411 자동 게시"]];
 flow.forEach((r,i)=>{ const l=64+i*296; box(s,`flow-${i}`,l,404,248,104,i===2?C.paleGreen:C.canvas,i===2?C.green:C.line); txt(s,`flow-a-${i}`,r[0],l+16,424,216,28,19,true,i===2?C.green:C.blue,"center"); txt(s,`flow-b-${i}`,r[1],l+16,466,216,28,18,false,C.ink,"center"); });
 txt(s,"safe","내부 Citation·Source 식별정보 노출 0건",100,564,1080,42,24,true,C.green,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"실패를 버리지 않고 같은 작업으로 수렴시킵니다",4);
 const states=[["OPEN","최초 실패"],["RETRY","1·2·4초"],["DLQ","3회 초과"],["RECOVERED","동일 작업 성공"]];
 states.forEach((r,i)=>{ const l=56+i*302; if(i<3) txt(s,`arrow-${i}`,"→",l+246,278,50,42,28,true,C.gray,"center"); box(s,`state-${i}`,l,206,240,176,i===3?C.paleGreen:C.canvas,i===3?C.green:C.line); txt(s,`state-title-${i}`,r[0],l+18,238,204,42,25,true,i===3?C.green:C.blue,"center"); txt(s,`state-copy-${i}`,r[1],l+18,304,204,34,20,false,C.ink,"center"); });
 box(s,"notif",170,464,940,100,C.pale,C.blue); txt(s,"notif-text","장애 알림 1회 · 복구 알림 1회 · 정상 주기 알림 0회 · 알림 실패 0건",200,495,880,40,24,true,C.blue,"center");
 txt(s,"checkpoint","실패 Post는 체크포인트하지 않아 다음 Poll에서 자동 재처리",100,592,1080,38,22,true,C.gray,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"배포 후 Chat과 Community가 모두 정상 서비스 중입니다",5);
 metric(s,"gateway","Healthy","AI Gateway",52,148,260,C.green); metric(s,"poller","Running","Community Poller",354,148,260,C.green); metric(s,"http","200 × 3","공개 Endpoint",656,148,260,C.blue); metric(s,"guard","0","보호 서비스 변경",958,148,260,C.green);
 const rows=[["Community","HTTP 200"],["Chat","HTTP 200"],["Activepieces","HTTP 200"],["Poller","정상 67회"],["기동 실패","1회 자동 복구"]];
 rows.forEach((r,i)=>{ const l=58+i*238; box(s,`check-${i}`,l,394,206,92,C.canvas,C.line); txt(s,`check-title-${i}`,r[0],l+14,412,178,28,18,true,C.gray,"center"); txt(s,`check-value-${i}`,r[1],l+14,450,178,28,19,true,C.ink,"center"); });
 txt(s,"backup",`Rollback backup · ${data.release.backupRoot.split('/').pop()}`,100,562,1080,40,22,true,C.blue,"center"); notes(s);
}
{
 const s=deck.slides.add(); s.background.fill=C.white; title(s,"Epic #5는 ABLESTACK Assist MVP 제품화입니다",6);
 const items=[["Tenant·RBAC","격리·보존·삭제"],["SSO·Identity","세 채널 동일 권한"],["Release 지식","Diplo 현재·Europa Preview"],["제품 UI Assist","Case·Artifact·Conversation"],["HA·SLO·보안","99.9%·복구 훈련"],["Pilot·Beta","90% 답변·95% 보류"]];
 items.forEach((r,i)=>{ const l=54+(i%3)*404, t=138+Math.floor(i/3)*174; box(s,`item-${i}`,l,t,356,132,i<2?C.pale:C.canvas,i<2?C.blue:C.line); txt(s,`item-title-${i}`,r[0],l+22,t+24,312,32,22,true,i<2?C.blue:C.ink,"center"); txt(s,`item-copy-${i}`,r[1],l+22,t+75,312,30,18,false,C.gray,"center"); });
 box(s,"next",164,538,952,88,C.paleGreen,C.green); txt(s,"next-text","첫 작업 · Tenant·RBAC 경계 + 제품 UX 계약 Architecture Baseline",194,565,892,36,24,true,C.green,"center"); notes(s);
}

for (const [index,slide] of deck.slides.items.entries()) { const stem=`slide-${String(index+1).padStart(2,"0")}`; const png=await deck.export({slide,format:"png",scale:1}); await fs.writeFile(path.join(renderDir,`${stem}.png`),new Uint8Array(await png.arrayBuffer())); const layout=await slide.export({format:"layout"}); await fs.writeFile(path.join(renderDir,`${stem}.layout.json`),await layout.text()); }
const montage=await deck.export({format:"webp",montage:true,scale:1}); await fs.writeFile(path.join(renderDir,"montage.webp"),new Uint8Array(await montage.arrayBuffer()));
const pptx=await PresentationFile.exportPptx(deck); await pptx.save(output); console.log(output);

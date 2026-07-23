(function () {
  const q = selector => document.querySelector(selector);
  const filters = document.querySelectorAll("[data-period]");
  const list = q("#recordsList"), loading = q("#recordsLoading"), empty = q("#recordsEmpty"), errorBox = q("#recordsError");
  const detailOverlay = q("#recordDetailOverlay"), detailContent = q("#recordDetailContent"), formOverlay = q("#recordFormOverlay");
  let user = null, period = "all", itemSequence = 0, mediaObjectUrls = [], activeDetailId = null;

  function getUser() { try { const value=JSON.parse(sessionStorage.getItem("gymfitUser")||"null"); const id=Number(value?.user_id??value?.userId); return id>0?{...value,user_id:id}:null; } catch{return null;} }
  async function api(url, options={}) { const response=await fetch(url,{...options,headers:{...(options.body && !(options.body instanceof FormData)?{"Content-Type":"application/json"}:{}),"X-User-Id":String(user.user_id),...(options.headers||{})}}); const body=response.status===204?null:await response.json().catch(()=>null); if(!response.ok) throw new Error(body?.detail||"요청을 처리하지 못했습니다."); return body; }
  const esc = value => String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
  function localDate(value){ const match=String(value||"").match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/); return match?new Date(+match[1],+match[2]-1,+match[3],+match[4],+match[5]):null; }
  const formatDate=value=>{const date=localDate(value)||new Date(`${value}T00:00:00`);return new Intl.DateTimeFormat("ko-KR",{year:"numeric",month:"long",day:"numeric",weekday:"short"}).format(date);};
  const formatTime=value=>{const date=localDate(value);return date?new Intl.DateTimeFormat("ko-KR",{hour:"2-digit",minute:"2-digit",hour12:false}).format(date):"";};
  function state(name,message=""){loading.hidden=name!=="loading";empty.hidden=name!=="empty";errorBox.hidden=name!=="error";list.hidden=name!=="ready";if(name==="error")q("#recordsErrorMessage").textContent=message;}

  function render(data){ q("#recordTotalCount").textContent=Number(data.total)||0; list.replaceChildren(); if(!data.items?.length){state("empty");return;} let lastDate="";
    data.items.forEach(item=>{if(item.workout_date!==lastDate){lastDate=item.workout_date;const group=document.createElement("h2");group.className="record-date-group";group.textContent=formatDate(item.workout_date);list.append(group);} const card=document.createElement("button");card.type="button";card.className=`record-card ${item.record_type==="PT"?"pt-record-card":""}`;card.setAttribute("aria-label",`${item.title} 상세 보기`);
      const names=(item.exercise_names||[]).slice(0,3).join(" · ");card.innerHTML=`<div class="record-card-heading"><div class="record-title-line"><h2>${esc(item.title)}</h2><span class="record-type ${item.record_type.toLowerCase()}">${item.record_type==="PT"?"PT":"일반 운동"}</span></div><p>${esc(formatTime(item.started_at))}${item.completed_at?` ~ ${esc(formatTime(item.completed_at))}`:""}${item.workout_part?` · ${esc(item.workout_part)}`:""}</p>${item.trainer_name?`<p class="record-trainer">${esc(item.trainer_name)} 트레이너</p>`:""}</div><div class="record-card-summary"><strong>${Number(item.workout_minutes)||0}<small>분</small></strong><span>${Number(item.item_count)||0}개 운동</span>${item.has_media?'<span class="media-mark">미디어 있음</span>':""}<i aria-hidden="true">›</i></div>${names?`<p class="record-exercise-names">${esc(names)}</p>`:""}`;
      card.addEventListener("click",()=>openDetail(item.workout_record_id));list.append(card);});state("ready");}
  async function load(){state("loading");try{render(await api(`/api/workout-sessions?period=${period}&limit=100&offset=0`));}catch(error){state("error",error.message);}}

  function optionalRow(label,value){return value!==null&&value!==undefined&&value!==""?`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`:"";}
  async function loadProtectedMedia(media, element){try{const response=await fetch(media.media_url,{headers:{"X-User-Id":String(user.user_id)}});if(!response.ok)throw new Error();const url=URL.createObjectURL(await response.blob());mediaObjectUrls.push(url);element.src=url;}catch{element.replaceWith(Object.assign(document.createElement("p"),{textContent:"미디어를 불러오지 못했습니다."}));}}
  function clearMediaUrls(){mediaObjectUrls.forEach(URL.revokeObjectURL);mediaObjectUrls=[];}
  async function openDetail(id){activeDetailId=id;clearMediaUrls();detailOverlay.hidden=false;document.body.classList.add("detail-open");q("#recordDetailLoading").hidden=false;q("#recordDetailError").hidden=true;detailContent.hidden=true;try{const data=await api(`/api/workout-sessions/${id}`);q("#recordDetailTitle").textContent=data.title||"PT 수업";const typeBadge=q("#recordDetailType");typeBadge.textContent=data.record_type==="PT"?"PT":"일반 운동";typeBadge.className=`record-type ${data.record_type.toLowerCase()}`;const meta=[optionalRow("날짜",formatDate(data.workout_date)),optionalRow("시간",`${formatTime(data.started_at)}${data.completed_at?` ~ ${formatTime(data.completed_at)}`:""}`),optionalRow("운동 시간",data.workout_minutes?`${data.workout_minutes}분`:null),optionalRow("운동 부위",data.workout_part),optionalRow("트레이너",data.trainer_name),data.record_type==="PT"?"":optionalRow("장소",data.location),optionalRow("메모",data.memo)].join("");
        const workoutOnly = data.record_type === "WORKOUT" ? [optionalRow("칼로리",data.calories?`${data.calories}kcal`:null),optionalRow("평균 자세 점수",data.posture_score!==null?`${data.posture_score}점`:null),optionalRow("최고 자세 점수",data.best_posture_score!==null?`${data.best_posture_score}점`:null)].join("") : "";
        const aiSection = data.record_type === "WORKOUT" && (data.feedback_title || data.feedback || data.image_url) ? `<section class="session-ai-feedback"><span>AI 자세 피드백</span>${data.feedback_title?`<strong>${esc(data.feedback_title)}</strong>`:""}${data.feedback?`<p>${esc(data.feedback)}</p>`:""}${data.image_url?`<img src="${esc(data.image_url)}" alt="베스트 자세 이미지">`:""}</section>` : "";
        const emptyExercises=!data.items.length?`<div class="detail-exercise-empty"><strong>등록된 운동 상세가 없습니다</strong><p>PT 수업 시간만 기록되었습니다.</p></div>`:"";detailContent.innerHTML=`<dl class="session-meta">${meta}${workoutOnly}</dl>${aiSection}<section class="detail-exercises"><h3>수행 운동${data.items.length?` <span>${data.items.length}</span>`:""}</h3>${emptyExercises}<div id="detailExerciseList"></div></section>`;const itemList=q("#detailExerciseList");
        data.items.forEach((item,index)=>{const card=document.createElement("article");card.className="detail-exercise-card";const weight=item.weight_text|| (item.weight_value!==null?`${item.weight_value}kg`:null);const summary=[weight,item.repetitions?`${item.repetitions}회`:null,item.completed_sets?`${item.completed_sets}세트`:null].filter(Boolean).join(" · ");const metrics=[optionalRow("무게",weight),optionalRow("횟수",item.repetitions?`${item.repetitions}회`:null),optionalRow("세트",item.completed_sets?`${item.completed_sets}세트`:null),optionalRow("RPE",item.rpe),optionalRow("운동 시간",item.workout_minutes?`${item.workout_minutes}분`:null),data.record_type==="PT"?"":optionalRow("자세 점수",item.posture_score!==null?`${item.posture_score}점`:null),optionalRow("메모",item.memo)].join("");const hasMedia=Boolean(item.media?.length);card.innerHTML=`<button type="button" class="exercise-toggle" aria-expanded="false"><b>${index+1}</b><span class="exercise-toggle-copy"><strong>${esc(item.exercise_name)}</strong>${summary?`<small>${esc(summary)}</small>`:""}</span>${hasMedia?'<i class="exercise-media-mark">미디어</i>':""}<span class="exercise-chevron" aria-hidden="true">⌄</span></button><div class="exercise-detail" hidden>${metrics?`<dl>${metrics}</dl>`:""}${hasMedia?'<div class="exercise-media"></div>':""}</div>`;const body=card.querySelector(".exercise-detail"),toggle=card.querySelector(".exercise-toggle");toggle.addEventListener("click",()=>{body.hidden=!body.hidden;toggle.setAttribute("aria-expanded",String(!body.hidden));});const mediaBox=card.querySelector(".exercise-media");
          (item.media||[]).forEach(media=>{const element=document.createElement(media.media_type==="VIDEO"?"video":"img");if(media.media_type==="VIDEO"){element.controls=true;element.playsInline=true;element.preload="metadata";}else{element.tabIndex=0;element.addEventListener("click",()=>element.classList.toggle("expanded"));element.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();element.click();}});}element.alt=`${item.exercise_name} 운동 미디어`;mediaBox.append(element);loadProtectedMedia(media,element);});itemList.append(card);});
        q("#recordDetailLoading").hidden=true;detailContent.hidden=false;history.pushState({recordId:id},"",`/records/${id}`);}catch(error){q("#recordDetailLoading").hidden=true;q("#recordDetailError").hidden=false;q("#recordDetailErrorMessage").textContent=error.message;}}
  function closeDetail(update=true){detailOverlay.querySelectorAll("video").forEach(video=>video.pause());detailOverlay.hidden=true;document.body.classList.remove("detail-open");clearMediaUrls();activeDetailId=null;if(update&&location.pathname!=="/records")history.pushState({},"","/records");}

  function itemEditor(){const id=++itemSequence,wrap=document.createElement("article");wrap.className="record-item-input";wrap.dataset.itemKey=String(id);wrap.innerHTML=`<header><strong>운동 ${q("#recordItemList").children.length+1}</strong><div><button type="button" data-move="up">↑</button><button type="button" data-move="down">↓</button><button type="button" data-remove>삭제</button></div></header><label><span>운동명</span><input data-field="exercise_name" maxlength="100" required></label><div class="record-form-grid"><label><span>무게(kg)</span><input data-field="weight_value" type="number" min="0" step="0.1"></label><label><span>무게 표시</span><input data-field="weight_text" maxlength="100" placeholder="맨몸, 밴드 등"></label><label><span>횟수</span><input data-field="repetitions" type="number" min="1"></label><label><span>세트</span><input data-field="completed_sets" type="number" min="1"></label><label><span>RPE</span><input data-field="rpe" type="number" min="1" max="10"></label><label><span>운동 시간(분)</span><input data-field="workout_minutes" type="number" min="1"></label></div><label><span>운동 메모</span><textarea data-field="memo" rows="2"></textarea></label><label><span>짧은 영상 또는 이미지</span><input data-media type="file" multiple accept="video/mp4,video/webm,image/jpeg,image/png,image/webp"></label>`;
    wrap.querySelector("[data-remove]").onclick=()=>wrap.remove();wrap.querySelector('[data-move="up"]').onclick=()=>wrap.previousElementSibling&&wrap.parentNode.insertBefore(wrap,wrap.previousElementSibling);wrap.querySelector('[data-move="down"]').onclick=()=>wrap.nextElementSibling&&wrap.parentNode.insertBefore(wrap.nextElementSibling,wrap);return wrap;}
  function openForm(){q("#recordForm").reset();q("#recordItemList").replaceChildren();const now=new Date(),end=new Date(now),start=new Date(now.getTime()-3600000);q("#recordDate").value=now.toISOString().slice(0,10);q("#recordStart").value=start.toTimeString().slice(0,5);q("#recordEnd").value=end.toTimeString().slice(0,5);q("#recordFormMessage").textContent="";formOverlay.hidden=false;document.body.classList.add("detail-open");}
  function closeForm(){formOverlay.hidden=true;document.body.classList.remove("detail-open");}
  function value(input){return input?.value.trim()||null;} function num(input){return value(input)!==null?Number(input.value):null;}
  q("#recordForm").addEventListener("submit", async event => {
    event.preventDefault();
    const button=q("#recordSave"), message=q("#recordFormMessage"), date=q("#recordDate").value;
    const editors=[...q("#recordItemList").children];
    const items=editors.map(editor=>({
      exercise_name:value(editor.querySelector('[data-field="exercise_name"]')),
      weight_value:num(editor.querySelector('[data-field="weight_value"]')),
      weight_text:value(editor.querySelector('[data-field="weight_text"]')),
      repetitions:num(editor.querySelector('[data-field="repetitions"]')),
      completed_sets:num(editor.querySelector('[data-field="completed_sets"]')),
      rpe:num(editor.querySelector('[data-field="rpe"]')),
      workout_minutes:num(editor.querySelector('[data-field="workout_minutes"]')),
      memo:value(editor.querySelector('[data-field="memo"]')),
    }));
    button.disabled=true; message.textContent="";
    try {
      const created=await api("/api/workout-sessions",{method:"POST",body:JSON.stringify({
        title:value(q("#recordTitle")), workout_date:date,
        started_at:`${date}T${q("#recordStart").value}:00`, completed_at:`${date}T${q("#recordEnd").value}:00`,
        workout_part:q("#recordPart").value||null, location:value(q("#recordLocation")),
        memo:value(q("#recordMemo")), items,
      })});
      let mediaError=null;
      for(let index=0;index<editors.length;index++){
        for(const file of editors[index].querySelector("[data-media]").files){
          try {
            const form=new FormData(); form.append("file",file);
            await api(`/api/workout-sessions/items/${created.items[index].item_id}/media`,{method:"POST",body:form});
          } catch(error) { mediaError=error; }
        }
      }
      closeForm(); await load();
      if(mediaError) alert(`운동 기록은 저장됐지만 일부 미디어를 업로드하지 못했습니다.\n${mediaError.message}`);
    } catch(error) { message.textContent=error.message; }
    finally { button.disabled=false; }
  });
  q("#addRecordItem").onclick=()=>q("#recordItemList").append(itemEditor());q("#openRecordForm").onclick=openForm;q("#recordFormClose").onclick=closeForm;q("#recordFormBackdrop").onclick=closeForm;
  q("#recordDetailClose").onclick=()=>closeDetail();q("#recordDetailBackdrop").onclick=()=>closeDetail();q("#recordsRetryButton").onclick=load;
  q("#recordDetailRetry").onclick=()=>activeDetailId&&openDetail(activeDetailId);
  filters.forEach(button=>button.onclick=()=>{period=button.dataset.period;filters.forEach(item=>item.classList.toggle("active",item===button));load();});
  addEventListener("popstate",()=>{const match=location.pathname.match(/^\/records\/(\d+)/);if(match)openDetail(Number(match[1]));else closeDetail(false);});
  addEventListener("commonLayoutReady",()=>{user=getUser();if(!user){location.href="/login";return;}if(String(user.account_type??user.accountType??"").toUpperCase()==="TRAINER")q("#openRecordForm").hidden=true;load();const match=location.pathname.match(/^\/records\/(\d+)/);if(match)openDetail(Number(match[1]));});
  addEventListener("keydown",event=>{if(event.key==="Escape"){if(!detailOverlay.hidden)closeDetail();else if(!formOverlay.hidden)closeForm();}});
})();

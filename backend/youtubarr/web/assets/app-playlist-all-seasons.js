/* Youtubarr v1.0.6 - complete-series playlist mapping.
 * Loaded after the base YouTube workflow so these functions intentionally
 * override the earlier single-season mapper without changing the Arr shell.
 */

function playlistRegularSeasonLabel(seasons){
  const regular=[...seasons].filter(s=>Number(s)>0).map(Number).sort((a,b)=>a-b);
  if(!regular.length)return 'All Seasons';
  const continuous=regular.every((s,i)=>i===0||s===regular[i-1]+1);
  if(continuous&&regular.length>1)return `All Seasons (${regular[0]}–${regular[regular.length-1]})`;
  return `All Seasons (${regular.join(', ')})`;
}

async function loadSeriesSeasons(){
  const id=Number($('#plSeries')?.value||0);if(!id)return;
  const eps=await api(`/api/series/${id}/episodes`);
  playlistState.allTargets=eps;

  const seasons=[...new Set(eps.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  const regular=seasons.filter(s=>s>0);
  const options=[];

  if(regular.length>1){
    options.push(`<option value="all-regular">${esc(playlistRegularSeasonLabel(regular))}</option>`);
  }

  for(const season of seasons){
    const label=season===0?'Season 0 (Specials)':`Season ${season}`;
    options.push(`<option value="${season}">${esc(label)}</option>`);
  }

  $('#plSeason').innerHTML=options.join('')||'<option value="">No seasons available</option>';

  // A series/season-level playlist search can hand its result straight into
  // Import Lists. Keep that context through the async Sonarr season lookup.
  let context=null;
  try{context=JSON.parse(sessionStorage.getItem('playlistContext')||'null')}catch{}
  if(context?.family==='series'&&Number(context.seriesId||0)===id){
    const requested=String(context.seasonSelection??'');
    if(requested&&[...$('#plSeason').options].some(o=>o.value===requested))$('#plSeason').value=requested;
    if(context.playlistUrl&&$('#plUrl'))$('#plUrl').value=context.playlistUrl;
  }
}

function orderedSeriesTargets(selection){
  const rows=[...(playlistState.allTargets||[])];
  let targets;

  if(selection==='all-regular'){
    targets=rows.filter(e=>Number(e.seasonNumber||0)>0);
  }else{
    const season=Number(selection);
    targets=rows.filter(e=>Number(e.seasonNumber||0)===season);
  }

  return targets.sort((a,b)=>(Number(a.seasonNumber||0)-Number(b.seasonNumber||0))||(Number(a.episodeNumber||0)-Number(b.episodeNumber||0)));
}

async function previewPlaylist(){
  const url=$('#plUrl')?.value.trim();if(!url)return toast('Paste a YouTube playlist URL','bad');
  $('#plPreviewPanel').innerHTML='<div class="empty">Reading YouTube playlist…</div>';

  try{
    playlistState.playlist=await api('/api/youtube/playlist',{method:'POST',body:JSON.stringify({url})});
    const entries=playlistState.playlist?.entries||[];
    const start=Math.max(1,Number($('#plStart')?.value||1))-1;
    playlistState.mappings=[];

    if(playlistState.family==='series'){
      const selection=$('#plSeason')?.value||'';
      const targets=orderedSeriesTargets(selection).slice(start);
      playlistState.targets=targets;
      playlistState.targetCount=targets.length;

      const pairCount=Math.min(entries.length,targets.length);
      const onlyMissing=Boolean($('#plMissing')?.checked);
      for(let i=0;i<pairCount;i++){
        const target=targets[i];
        const shouldQueue=!onlyMissing||(!youtubarrEpisodePresent(target)&&target.monitored!==false);
        playlistState.mappings.push({entry:entries[i],target,entryIndex:i,shouldQueue});
      }
    }else{
      const tracks=[...(playlistState.allTargets||[])].sort((a,b)=>(Number(a.mediumNumber||1)-Number(b.mediumNumber||1))||(Number(a.trackNumber||a.absoluteTrackNumber||0)-Number(b.trackNumber||b.absoluteTrackNumber||0))).slice(start);
      playlistState.targets=tracks;
      playlistState.targetCount=tracks.length;
      const pairCount=Math.min(entries.length,tracks.length);
      for(let i=0;i<pairCount;i++)playlistState.mappings.push({entry:entries[i],target:tracks[i],entryIndex:i,shouldQueue:true});
    }

    renderPlaylistPreview();
  }catch(e){
    $('#plPreviewPanel').innerHTML=`<div class="error-box">${esc(e.message)}</div>`;
  }
}

function renderPlaylistPreview(){
  const entries=playlistState.playlist?.entries||[];
  const mappings=playlistState.mappings||[];
  const queueable=mappings.filter(m=>m.shouldQueue!==false);
  const targetCount=Number(playlistState.targetCount??playlistState.targets?.length??0);
  const rows=[];

  for(let i=0;i<mappings.length;i++){
    const m=mappings[i],p=m.entry,t=m.target;
    const label=playlistState.family==='series'
      ? `S${String(t.seasonNumber).padStart(2,'0')}E${String(t.episodeNumber).padStart(2,'0')} · ${t.title}`
      : `${t.trackNumber||i+1}. ${t.title}`;
    const found=m.shouldQueue===false;
    rows.push(`<tr class="${found?'mapping-already-found':''}"><td><input class="plMapCheck" type="checkbox" data-map-index="${i}" ${found?'disabled':'checked'}></td><td>${esc(p.position??m.entryIndex+1)}</td><td><strong>${esc(p.title)}</strong><small>${fmtDur(p.duration||0)}</small></td><td>→</td><td><strong>${esc(label)}</strong>${found?'<small>Already available — skipped</small>':''}</td></tr>`);
  }

  const paired=mappings.length;
  const mismatch=entries.length!==targetCount;
  const mode=$('#plSeason')?.value==='all-regular'?'complete-series selection':'selected season/album';
  $('#plPreviewPanel').innerHTML=`<div class="playlist-summary"><strong>${esc(playlistState.playlist?.title||'YouTube playlist')}</strong><span>${entries.length} playlist items · ${targetCount} available targets · ${paired} paired · ${queueable.length} to queue</span></div>${mismatch?`<div class="warning-box">Playlist and target counts differ for this ${mode}. Only the first ${Math.min(entries.length,targetCount)} ordered pairs can be mapped. Review the preview before queuing.</div>`:''}<div class="arr-table-wrap"><table class="arr-table"><thead><tr><th></th><th>#</th><th>YouTube</th><th></th><th>${playlistState.family==='series'?'Sonarr Episode':'Lidarr Track'}</th></tr></thead><tbody>${rows.join('')||'<tr><td colspan="5"><div class="empty">Nothing could be mapped.</div></td></tr>'}</tbody></table></div><div class="playlist-actions"><button class="btn btn-primary" onclick="queuePlaylistMappings()" ${queueable.length?'':'disabled'}>Queue Selected Mappings</button></div>`;
}

async function queuePlaylistMappings(){
  const checks=$$('.plMapCheck:checked');if(!checks.length)return toast('Select at least one mapping','bad');
  const mappings=playlistState.mappings||[];
  let ok=0,failed=0,firstError='';

  for(const c of checks){
    const i=Number(c.dataset.mapIndex),mapping=mappings[i];
    if(!mapping)continue;
    const p=mapping.entry,t=mapping.target;
    try{
      await api('/api/acquisitions',{method:'POST',body:JSON.stringify({kind:playlistState.family==='series'?'episode':'track',remoteId:Number(t.id),youtubeUrl:p.url})});
      ok++;
    }catch(e){
      failed++;
      if(!firstError)firstError=e.message||String(e);
      c.closest('tr')?.classList.add('mapping-failed');
      c.title=e.message||String(e);
    }
  }

  const detail=failed&&firstError?` — ${firstError}`:'';
  toast(`${ok} mapped item${ok===1?'':'s'} queued${failed?`; ${failed} failed${detail}`:''}`,failed?'bad':'ok');
  if(ok)navigate('queue');
}

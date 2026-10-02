/* Youtubarr v1.0.9 - series library location management. */

async function seriesDetail(id){
  const series=(state.series.length?state.series:await api('/api/series')).find(x=>Number(x.id)===Number(id));
  const eps=await api(`/api/series/${id}/episodes`);
  if(!series)throw new Error('Series not found');
  const img=imageFor(series);
  const actions=actionButton('Refresh & Scan','refresh','route(true)')+
    actionButton('Search Monitored','search',`searchSeriesMissing(${Number(id)})`)+
    actionButton('Search Playlists','search',`searchSeriesPlaylists(${Number(id)},null)`)+
    actionButton('Import Playlist','list',`openSeriesPlaylist(${Number(id)})`)+
    actionButton('Change Location','list',`openSeriesLocation(${Number(id)})`);
  $('#main').innerHTML=actionBar(actions,toolbarMenu('detailFilter',{label:'Filter',options:[{label:'All episodes',action:'void 0'},{label:'Missing only',action:'void 0'}]}))+`<div class="content"><div class="series-hero"><div class="series-hero-poster">${img?`<img src="${esc(img)}" onerror="this.style.display='none'">`:posterFallback(series.title)}</div><div class="series-hero-info"><h1>${esc(series.title)}</h1><div class="meta-line"><span>${series.year||''}</span><span>${esc(series.network||'')}</span><span>${esc(series.status||'')}</span></div><p>${esc(series.overview||'')}</p><div class="path-line">${esc(series.path||'')}</div></div></div>${episodeTable(eps,series.title||'',Number(id))}</div>`;
}

function closeSeriesLocation(){
  document.getElementById('seriesLocationOverlay')?.remove();
}

async function openSeriesLocation(seriesId){
  closeSeriesLocation();
  const overlay=document.createElement('div');
  overlay.className='arr-modal-overlay';
  overlay.id='seriesLocationOverlay';
  overlay.innerHTML=`<div class="arr-modal series-location-modal"><div class="arr-modal-head"><strong>Change Library Location</strong><button class="icon-btn" onclick="closeSeriesLocation()">×</button></div><div class="arr-modal-body"><div class="empty">Loading Sonarr root folders…</div></div></div>`;
  overlay.addEventListener('click',event=>{if(event.target===overlay)closeSeriesLocation()});
  document.body.appendChild(overlay);

  try{
    const data=await api(`/api/series/${Number(seriesId)}/locations`);
    const roots=data.roots||[];
    const body=overlay.querySelector('.arr-modal-body');
    if(!roots.length){
      body.innerHTML=`<div class="error-box">No Youtubarr TV roots are configured in Sonarr. Add roots such as <code>/youtube-library/tv/kids</code> and <code>/youtube-library/tv/shows</code> in Sonarr first.</div>`;
      return;
    }
    body.innerHTML=`
      <p class="help">Move this series between Youtubarr TV roots without downloading the YouTube media again. Existing symlinks are moved, Youtubarr output paths are repaired and Sonarr is asked to rescan.</p>
      <div class="series-location-current"><span>Current Sonarr path</span><code>${esc(data.seriesPath||'')}</code></div>
      <label class="series-location-label" for="seriesLocationRoot">Destination root</label>
      <select id="seriesLocationRoot" class="series-location-select">
        ${roots.map(root=>`<option value="${esc(root.path)}" ${root.current?'selected':''}>${esc(root.label||root.path)}${root.current?' — current':''}</option>`).join('')}
      </select>
      <div class="series-location-note">You can select the current root as a repair operation. That is useful if Sonarr was moved manually but Youtubarr's existing symlinks are still under the old root.</div>
      <div id="seriesLocationResult"></div>
      <div class="arr-modal-actions"><button class="btn" onclick="closeSeriesLocation()">Cancel</button><button class="btn btn-primary" id="seriesLocationApply">Move / Repair Series</button></div>`;
    document.getElementById('seriesLocationApply').onclick=()=>applySeriesLocation(Number(seriesId));
  }catch(e){
    overlay.querySelector('.arr-modal-body').innerHTML=`<div class="error-box">${esc(e.message)}</div>`;
  }
}

async function applySeriesLocation(seriesId){
  const select=document.getElementById('seriesLocationRoot');
  const button=document.getElementById('seriesLocationApply');
  const result=document.getElementById('seriesLocationResult');
  const rootPath=select?.value||'';
  if(!rootPath)return toast('Choose a destination root','bad');
  button.disabled=true;
  button.textContent='Moving…';
  if(result)result.innerHTML='<div class="empty">Moving Youtubarr symlinks and updating Sonarr…</div>';
  try{
    const data=await api(`/api/series/${Number(seriesId)}/location`,{method:'POST',body:JSON.stringify({rootPath})});
    const warnings=[];
    if(data.missingSources)warnings.push(`${data.missingSources} completed acquisition${data.missingSources===1?' has':'s have'} no visible source symlink`);
    if(!data.rescanQueued)warnings.push(`Sonarr rescan was not queued: ${data.rescanError||'unknown error'}`);
    if(data.activeAcquisitionsWatching)warnings.push(`${data.activeAcquisitionsWatching} active acquisition${data.activeAcquisitionsWatching===1?' is':'s are'} being watched for late output`);
    if(result)result.innerHTML=`<div class="success-box"><strong>${esc(data.title||'Series')} moved/repaired.</strong><div>${Number(data.movedLinks||0)} symlink${Number(data.movedLinks||0)===1?'':'s'} moved · ${Number(data.updatedAcquisitions||0)} acquisition record${Number(data.updatedAcquisitions||0)===1?'':'s'} updated.</div><code>${esc(data.seriesPath||'')}</code>${warnings.length?`<div class="series-location-warnings">${warnings.map(esc).join('<br>')}</div>`:''}</div>`;
    state.series=[];
    toast('Series library location updated');
    setTimeout(()=>{closeSeriesLocation();navigate('series',`id=${Number(seriesId)}`)},900);
  }catch(e){
    if(result)result.innerHTML=`<div class="error-box">${esc(e.message)}</div>`;
    button.disabled=false;
    button.textContent='Move / Repair Series';
  }
}

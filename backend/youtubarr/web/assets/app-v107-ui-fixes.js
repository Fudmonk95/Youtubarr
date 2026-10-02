/* Youtubarr v1.0.7 - Arr menu behaviour + Youtubarr-aware progress UI. */

function closeToolMenus(exceptId=''){
  $$('.tool-menu.open').forEach(menu=>{
    if(!exceptId||menu.id!==exceptId)menu.classList.remove('open');
  });
}

function toggleToolMenu(id,event){
  if(event)event.stopPropagation();
  const menu=document.getElementById(id);
  if(!menu)return;
  const shouldOpen=!menu.classList.contains('open');
  closeToolMenus();
  if(shouldOpen)menu.classList.add('open');
}

function toolbarMenu(id,items){
  return `<div class="tool-menu-wrap" onclick="event.stopPropagation()"><button class="action-button" onclick="toggleToolMenu('${id}',event)">${icon('list')}<span>${items.label}</span></button><div class="tool-menu" id="${id}">${items.options.map(o=>`<button onclick="event.stopPropagation();closeToolMenus();${o.action}">${o.label}</button>`).join('')}</div></div>`;
}

if(!window.__youtubarrExclusiveMenus){
  window.__youtubarrExclusiveMenus=true;
  document.addEventListener('click',()=>closeToolMenus());
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape')closeToolMenus();
  });
}

function youtubarrEpisodePresent(e){
  return Boolean(
    e?.hasFile || e?.arrHasFile || e?.youtubarrHasFile ||
    e?.availability==='registered' || e?.availability==='youtubarr'
  );
}

function youtubarrSeriesProgress(series){
  const stats=series?.statistics||{};
  const total=Number(
    series?.episodeCount ??
    stats.episodeCount ??
    stats.totalEpisodeCount ??
    0
  )||0;
  const available=Number(
    series?.availableEpisodeCount ??
    stats.availableEpisodeCount ??
    stats.episodeFileCount ??
    0
  )||0;
  const bounded=total?Math.min(total,Math.max(0,available)):Math.max(0,available);
  const pct=total?Math.max(0,Math.min(100,Math.round((bounded/total)*100))):0;
  return {total,available:bounded,pct,complete:Boolean(total&&bounded>=total)};
}

function seriesPosterGrid(rows){
  return `<div class="arr-poster-grid" id="seriesGrid">${rows.map(series=>{
    const img=imageFor(series);
    const progress=youtubarrSeriesProgress(series);
    const progressTitle=progress.total?`${progress.available} of ${progress.total} episodes available`:'No episode statistics';
    return `<article class="arr-poster-card" onclick="if(!document.getElementById('seriesGrid')?.classList.contains('select-mode'))navigate('series','id=${Number(series.id)}')">
      <input type="checkbox" class="poster-check" data-id="${Number(series.id)}" onclick="event.stopPropagation()">
      <div class="arr-poster ${img?'':'broken'}">
        ${img?`<img src="${esc(img)}" alt="${esc(series.title||'')}" onerror="this.style.display='none';this.parentNode.classList.add('broken')">`:posterFallback(series.title||'')}
        <div class="poster-progress-track ${progress.total?'':'no-data'}" title="${esc(progressTitle)}"><div class="poster-progress-fill ${progress.complete?'complete':''}" style="width:${progress.pct}%"></div></div>
      </div>
      <div class="arr-poster-foot">
        <strong>${esc(series.title||'')}</strong>
        <span>${series.monitored?'Monitored':'Unmonitored'}</span>
        <span>${esc(series.qualityProfile?.name||series.profileName||'')}</span>
        ${progress.total?`<span class="poster-progress-label ${progress.complete?'complete':''}">${progress.available} / ${progress.total} episodes</span>`:''}
      </div>
    </article>`;
  }).join('')||'<div class="empty">No series returned from Sonarr.</div>'}</div>`;
}

function youtubarrSeasonLabel(season){
  return Number(season)===0?'Specials':`Season ${Number(season)}`;
}

function episodeTable(eps,seriesTitle='',seriesId=0){
  const seasons=[...new Set(eps.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  return seasons.map(season=>{
    const rows=eps.filter(e=>Number(e.seasonNumber||0)===season).sort((a,b)=>Number(a.episodeNumber||0)-Number(b.episodeNumber||0));
    const available=rows.filter(youtubarrEpisodePresent).length;
    const total=rows.length;
    const pct=total?Math.round((available/total)*100):0;
    const complete=Boolean(total&&available===total);
    return `<section class="season-panel season-panel-progress">
      <div class="season-head season-head-progress">
        <div class="season-title-block">
          <strong>${esc(youtubarrSeasonLabel(season))}</strong>
          <span class="season-count ${complete?'complete':''}">${available} / ${total}</span>
        </div>
        <div class="season-head-actions">
          ${Number(seriesId)?`<button class="mini-btn season-playlist-search" title="Search YouTube playlists for ${esc(youtubarrSeasonLabel(season))}" onclick="searchSeriesPlaylists(${Number(seriesId)},${Number(season)})">${icon('search')}<span>Playlists</span></button>`:''}
        </div>
      </div>
      <div class="season-progress-track" title="${available} of ${total} episodes available"><div class="season-progress-fill ${complete?'complete':''}" style="width:${pct}%"></div></div>
      <table class="arr-table">
        <thead><tr><th>Episode</th><th>Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead>
        <tbody>${rows.map(e=>{
          const present=youtubarrEpisodePresent(e);
          return `<tr><td>${Number(e.seasonNumber||0)}x${String(Number(e.episodeNumber||0)).padStart(2,'0')}</td><td>${esc(e.title||'')}</td><td>${esc(e.airDate||String(e.airDateUtc||'').slice(0,10))}</td><td>${mediaAvailabilityBadge(e)}</td><td>${present?'':targetButton('episode',e.id,e.title||'',seriesTitle,e.seasonNumber,e.episodeNumber)}</td></tr>`;
        }).join('')}</tbody>
      </table>
    </section>`;
  }).join('');
}

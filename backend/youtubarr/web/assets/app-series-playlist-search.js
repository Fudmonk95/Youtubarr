/* Youtubarr v1.0.6 - series-level playlist hard search + Sonarr-style season progress. */

function youtubarrEpisodePresent(e){
  return Boolean(
    e?.hasFile || e?.arrHasFile || e?.youtubarrHasFile ||
    e?.availability==='registered' || e?.availability==='youtubarr'
  );
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
    const complete=total>0&&available===total;
    return `<section class="season-panel season-panel-progress">
      <div class="season-head season-head-progress">
        <div class="season-title-block"><strong>${esc(youtubarrSeasonLabel(season))}</strong><span class="season-count ${complete?'complete':''}">${available} / ${total}</span></div>
        <div class="season-head-actions">
          <button class="mini-btn season-playlist-search" title="Search YouTube playlists for ${esc(youtubarrSeasonLabel(season))}" onclick="searchSeriesPlaylists(${Number(seriesId)},${Number(season)})">${icon('search')}<span>Playlists</span></button>
        </div>
      </div>
      <div class="season-progress-track" title="${available} of ${total} episodes available"><div class="season-progress-fill ${complete?'complete':''}" style="width:${pct}%"></div></div>
      <table class="arr-table"><thead><tr><th>Episode</th><th>Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead><tbody>${rows.map(e=>{
        const present=youtubarrEpisodePresent(e);
        return `<tr><td>${Number(e.seasonNumber||0)}x${String(Number(e.episodeNumber||0)).padStart(2,'0')}</td><td>${esc(e.title||'')}</td><td>${esc(e.airDate||String(e.airDateUtc||'').slice(0,10))}</td><td>${mediaAvailabilityBadge(e)}</td><td>${present?'':targetButton('episode',e.id,e.title||'',seriesTitle,e.seasonNumber,e.episodeNumber)}</td></tr>`;
      }).join('')}</tbody></table>
    </section>`;
  }).join('');
}

async function seriesDetail(id){
  const series=(state.series.length?state.series:await api('/api/series')).find(x=>Number(x.id)===Number(id));
  const eps=await api(`/api/series/${id}/episodes`);
  if(!series)throw new Error('Series not found');
  const img=imageFor(series);
  const actions=actionButton('Refresh & Scan','refresh','route(true)')+
    actionButton('Search Monitored','search',`searchSeriesMissing(${Number(id)})`)+
    actionButton('Search Playlists','search',`searchSeriesPlaylists(${Number(id)},null)`)+
    actionButton('Import Playlist','list',`openSeriesPlaylist(${Number(id)})`);
  $('#main').innerHTML=actionBar(actions,toolbarMenu('detailFilter',{label:'Filter',options:[{label:'All episodes',action:'void 0'},{label:'Missing only',action:'void 0'}]}))+`<div class="content"><div class="series-hero"><div class="series-hero-poster">${img?`<img src="${esc(img)}" onerror="this.style.display='none'">`:posterFallback(series.title)}</div><div class="series-hero-info"><h1>${esc(series.title)}</h1><div class="meta-line"><span>${series.year||''}</span><span>${esc(series.network||'')}</span><span>${esc(series.status||'')}</span></div><p>${esc(series.overview||'')}</p><div class="path-line">${esc(series.path||'')}</div></div></div>${episodeTable(eps,series.title||'',Number(id))}</div>`;
}

function playlistSearchQuery(title,season=null){
  if(season===null||season===undefined||season==='')return `${title} full series complete episodes playlist`;
  if(Number(season)===0)return `${title} specials full episodes playlist`;
  return `${title} season ${Number(season)} full episodes playlist`;
}

async function searchSeriesPlaylists(seriesId,season=null){
  const rows=state.series.length?state.series:await api('/api/series');
  const series=rows.find(s=>Number(s.id)===Number(seriesId));
  if(!series)return toast('Series not found','bad');
  const query=playlistSearchQuery(series.title||'',season);
  sessionStorage.setItem('playlistHardSearch',JSON.stringify({seriesId:Number(seriesId),season,title:series.title||'',query}));
  renderSeriesPlaylistSearch(series,season,query);
  await runSeriesPlaylistSearch(Number(seriesId),season);
}

function renderSeriesPlaylistSearch(series,season,query){
  const scope=season===null||season===undefined?'Complete Series':youtubarrSeasonLabel(season);
  $('#main').innerHTML=actionBar(actionButton('Back','arrow',`navigate('series','id=${Number(series.id)}')`)+actionButton('Search','search',`runSeriesPlaylistSearch(${Number(series.id)},${season===null||season===undefined?'null':Number(season)})`))+`<div class="content"><h1>YouTube Playlist Search</h1><div class="playlist-search-context"><strong>${esc(series.title||'')}</strong><span>${esc(scope)}</span></div><div class="search-box-arr"><input id="playlistSearchQ" value="${esc(query)}" placeholder="Search YouTube playlists"><button class="btn btn-primary" onclick="runSeriesPlaylistSearch(${Number(series.id)},${season===null||season===undefined?'null':Number(season)})">Search Playlists</button></div><p class="help">Playlist-only hard search. Choose a result to send it into the ordered Sonarr mapper.</p><div id="playlistSearchResults"><div class="empty">Searching YouTube playlists…</div></div></div>`;
  $('#playlistSearchQ').onkeydown=e=>{if(e.key==='Enter')runSeriesPlaylistSearch(Number(series.id),season)};
}

async function runSeriesPlaylistSearch(seriesId,season=null){
  const q=$('#playlistSearchQ')?.value.trim()||JSON.parse(sessionStorage.getItem('playlistHardSearch')||'{}').query||'';
  if(!q)return toast('Enter a playlist search','bad');
  const out=$('#playlistSearchResults');if(out)out.innerHTML='<div class="empty">Searching YouTube playlists…</div>';
  try{
    const searchUrl=`https://www.youtube.com/results?search_query=${encodeURIComponent(q)}&sp=EgIQAw%253D%253D`;
    const data=await api('/api/youtube/playlist',{method:'POST',body:JSON.stringify({url:searchUrl})});
    const rows=(data.entries||[]).slice(0,30);
    if(!out)return;
    out.innerHTML=rows.length?`<div class="playlist-search-results">${rows.map((p,i)=>{
      const playlistUrl=p.id?`https://www.youtube.com/playlist?list=${encodeURIComponent(p.id)}`:(p.url||'');
      return `<article class="playlist-search-card"><div class="playlist-search-icon">▶</div><div class="playlist-search-meta"><h3>${esc(p.title||`Playlist ${i+1}`)}</h3><p>YouTube playlist result${p.duration?` · ${fmtDur(p.duration)}`:''}</p></div><div class="playlist-search-actions"><a class="mini-btn" href="${esc(playlistUrl)}" target="_blank" rel="noopener">Open</a><button class="btn btn-primary" data-url="${esc(playlistUrl)}" data-series="${Number(seriesId)}" data-season="${season===null||season===undefined?'all-regular':Number(season)}" onclick="useSeriesPlaylistSearchResult(this)">Use Playlist</button></div></article>`;
    }).join('')}</div>`:'<div class="empty">No playlist results were returned. Try simplifying the search terms.</div>';
  }catch(e){if(out)out.innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

function useSeriesPlaylistSearchResult(el){
  const seriesId=Number(el.dataset.series||0);
  const seasonSelection=String(el.dataset.season||'all-regular');
  const playlistUrl=el.dataset.url||'';
  sessionStorage.setItem('playlistContext',JSON.stringify({family:'series',seriesId,seasonSelection,playlistUrl}));
  navigate('import-lists');
}

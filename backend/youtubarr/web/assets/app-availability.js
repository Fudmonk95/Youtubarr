/* Youtubarr availability overlay.
 * Loaded after the existing Arr shell and YouTube workflow scripts so it can
 * refine media status without changing the established navigation/layout.
 */

function mediaAvailabilityBadge(item){
  if(item?.availability==='registered'||item?.arrHasFile){
    return '<span class="quality-pill">Registered</span>';
  }
  if(item?.availability==='youtubarr'||item?.youtubarrHasFile){
    return '<span class="status complete">Found by Youtubarr</span>';
  }
  if(item?.hasFile){
    return '<span class="quality-pill">Available</span>';
  }
  return 'Missing';
}

function episodeTable(eps,seriesTitle=''){
  const seasons=[...new Set(eps.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  return seasons.map(season=>{
    const rows=eps.filter(e=>Number(e.seasonNumber||0)===season).sort((a,b)=>Number(a.episodeNumber||0)-Number(b.episodeNumber||0));
    const available=rows.filter(e=>e.hasFile).length;
    return `<section class="season-panel"><div class="season-head"><strong>Season ${season}</strong><span>${available} / ${rows.length}</span></div><table class="arr-table"><thead><tr><th>Episode</th><th>Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead><tbody>${rows.map(e=>`<tr><td>${Number(e.seasonNumber||0)}x${String(Number(e.episodeNumber||0)).padStart(2,'0')}</td><td>${esc(e.title||'')}</td><td>${esc(e.airDate||String(e.airDateUtc||'').slice(0,10))}</td><td>${mediaAvailabilityBadge(e)}</td><td>${e.hasFile?'':targetButton('episode',e.id,e.title||'',seriesTitle,e.seasonNumber,e.episodeNumber)}</td></tr>`).join('')}</tbody></table></section>`;
  }).join('');
}

async function albumTracks(id,title){
  const tracks=await api(`/api/music/albums/${id}/tracks`);
  $('#main').innerHTML=actionBar(
    actionButton('Back','arrow','history.back()')+
    actionButton('Import Playlist','list',`openMusicPlaylist(${Number(id)})`)
  )+`<div class="content"><h1>${esc(title)}</h1><table class="arr-table"><thead><tr><th>#</th><th>Track</th><th>Duration</th><th>Status</th><th></th></tr></thead><tbody>${tracks.map(t=>`<tr><td>${t.trackNumber||''}</td><td>${esc(t.title||'')}</td><td>${fmtDur(t.duration||0)}</td><td>${mediaAvailabilityBadge(t)}</td><td>${t.hasFile?'':targetButton('track',t.id,t.title||'',title)}</td></tr>`).join('')||'<tr><td colspan="5"><div class="empty">No tracks.</div></td></tr>'}</tbody></table></div>`;
}

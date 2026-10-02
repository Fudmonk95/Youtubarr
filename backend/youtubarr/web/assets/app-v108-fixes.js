/* Youtubarr v1.0.8 - complete-series filtering + resilient all-seasons playlist mapping. */

function youtubarrSeriesComplete(series){
  return Boolean(youtubarrSeriesProgress(series).complete);
}

/*
 * The normal Series working view should focus on media that still needs work.
 * Complete series remain available under Filter -> Complete / All.
 */
async function seriesPage(params){
  const id=params.get('id');
  if(id)return seriesDetail(Number(id));

  state.series=await api('/api/series');
  const view=sessionStorage.getItem('seriesView')||'posters';
  const sort=sessionStorage.getItem('seriesSort')||'title';
  const filter=sessionStorage.getItem('seriesFilter')||'incomplete';
  let rows=[...state.series];

  if(filter==='incomplete')rows=rows.filter(series=>!youtubarrSeriesComplete(series));
  if(filter==='complete')rows=rows.filter(youtubarrSeriesComplete);
  if(filter==='monitored')rows=rows.filter(series=>series.monitored);
  if(filter==='unmonitored')rows=rows.filter(series=>!series.monitored);

  rows.sort((a,b)=>sort==='year'
    ? Number(b.year||0)-Number(a.year||0)
    : String(a.sortTitle||a.title||'').localeCompare(String(b.sortTitle||b.title||''))
  );

  const actions=
    actionButton('Update Filtered','refresh','route(true)')+
    actionButton('RSS Sync','refresh','rssSync()')+
    actionButton('Select Series','check','toggleSeriesSelect()')+
    actionButton('Test Parsing','list','testParsing()');

  const right=
    toolbarMenu('optionsMenu',{label:'Options',options:[
      {label:'Refresh',action:'route(true)'},
      {label:'Show monitored only',action:"setSeriesFilter('monitored')"},
    ]})+
    toolbarMenu('viewMenu',{label:'View',options:[
      {label:'Posters',action:"setSeriesView('posters')"},
      {label:'Table',action:"setSeriesView('table')"},
    ]})+
    toolbarMenu('sortMenu',{label:'Sort',options:[
      {label:'Title',action:"setSeriesSort('title')"},
      {label:'Year',action:"setSeriesSort('year')"},
    ]})+
    toolbarMenu('filterMenu',{label:'Filter',options:[
      {label:'Incomplete',action:"setSeriesFilter('incomplete')"},
      {label:'Complete',action:"setSeriesFilter('complete')"},
      {label:'All',action:"setSeriesFilter('all')"},
      {label:'Monitored',action:"setSeriesFilter('monitored')"},
      {label:'Unmonitored',action:"setSeriesFilter('unmonitored')"},
    ]});

  $('#main').innerHTML=actionBar(actions,right)+
    `<div class="content">${view==='table'?seriesTable(rows):seriesPosterGrid(rows)}</div>`;
}

function parsePlaylistEpisodeToken(title){
  const value=String(title||'');
  const patterns=[
    /\bS\s*0*(\d{1,2})\s*E\s*0*(\d{1,3})\b/i,
    /\b(\d{1,2})\s*x\s*0*(\d{1,3})\b/i,
    /\b(?:season|series)\s*0*(\d{1,2})\D{0,24}(?:episode|ep)\s*0*(\d{1,3})\b/i,
    /\b(?:season|series)\s*0*(\d{1,2})\s*[-:]\s*(?:episode|ep)?\s*0*(\d{1,3})\b/i,
  ];
  for(const pattern of patterns){
    const match=value.match(pattern);
    if(match)return {season:Number(match[1]),episode:Number(match[2])};
  }
  return null;
}

function playlistEpisodeKey(season,episode){
  return `${Number(season)}:${Number(episode)}`;
}

function regularPlaylistSeasons(){
  return [...new Set((playlistState.allTargets||[])
    .map(item=>Number(item.seasonNumber||0))
    .filter(season=>season>0)
  )].sort((a,b)=>a-b);
}

function ensurePlaylistStartSeasonControl(){
  if(playlistState.family!=='series')return;
  const form=document.querySelector('.playlist-form');
  const episodeInput=document.getElementById('plStart');
  if(!form||!episodeInput)return;

  let label=document.getElementById('plStartSeasonLabel');
  let select=document.getElementById('plStartSeason');
  const episodeLabel=episodeInput.previousElementSibling;

  if(!label){
    label=document.createElement('label');
    label.id='plStartSeasonLabel';
    label.textContent='Start mapping at season';
    select=document.createElement('select');
    select.id='plStartSeason';
    form.insertBefore(label,episodeLabel);
    form.insertBefore(select,episodeLabel);
  }

  const seasons=regularPlaylistSeasons();
  const previous=Number(select.value||0);
  select.innerHTML=seasons.map(season=>`<option value="${season}">Season ${season}</option>`).join('');
  if(previous&&seasons.includes(previous))select.value=String(previous);

  const allSeasons=document.getElementById('plSeason')?.value==='all-regular';
  label.style.display=allSeasons?'':'none';
  select.style.display=allSeasons?'':'none';
}

const __v108RenderPlaylistMapper=window.renderPlaylistMapper;
if(typeof __v108RenderPlaylistMapper==='function'){
  window.renderPlaylistMapper=function(context=null){
    __v108RenderPlaylistMapper(context);
    if(playlistState.family==='series'){
      const seasonSelect=document.getElementById('plSeason');
      if(seasonSelect){
        seasonSelect.addEventListener('change',ensurePlaylistStartSeasonControl);
        ensurePlaylistStartSeasonControl();
      }
    }
  };
}

const __v108LoadSeriesSeasons=window.loadSeriesSeasons;
if(typeof __v108LoadSeriesSeasons==='function'){
  window.loadSeriesSeasons=async function(){
    await __v108LoadSeriesSeasons();
    ensurePlaylistStartSeasonControl();
  };
}

function sequentialTargetsFromStart(selection,startSeason,startEpisode){
  const ordered=orderedSeriesTargets(selection);
  if(selection!=='all-regular'){
    const wantedEpisode=Math.max(1,Number(startEpisode||1));
    const index=ordered.findIndex(item=>Number(item.episodeNumber||0)>=wantedEpisode);
    return index>=0?ordered.slice(index):[];
  }

  const wantedSeason=Math.max(1,Number(startSeason||regularPlaylistSeasons()[0]||1));
  const wantedEpisode=Math.max(1,Number(startEpisode||1));
  const index=ordered.findIndex(item=>
    Number(item.seasonNumber||0)>wantedSeason ||
    (Number(item.seasonNumber||0)===wantedSeason&&Number(item.episodeNumber||0)>=wantedEpisode)
  );
  return index>=0?ordered.slice(index):[];
}

function exactPlaylistMappings(entries,targets,onlyMissing){
  const targetByKey=new Map(targets.map(target=>[
    playlistEpisodeKey(target.seasonNumber,target.episodeNumber),target,
  ]));
  const mappings=[];
  let parsed=0;
  let matched=0;
  const parsedSeasons=[];

  entries.forEach((entry,index)=>{
    const token=parsePlaylistEpisodeToken(entry.title);
    if(!token)return;
    parsed++;
    parsedSeasons.push(token.season);
    const target=targetByKey.get(playlistEpisodeKey(token.season,token.episode));
    if(!target)return;
    matched++;
    mappings.push({
      entry,
      target,
      entryIndex:index,
      shouldQueue:!onlyMissing||(!youtubarrEpisodePresent(target)&&target.monitored!==false),
      detected:true,
    });
  });

  return {mappings,parsed,matched,parsedSeasons};
}

async function previewPlaylist(){
  const url=$('#plUrl')?.value.trim();
  if(!url)return toast('Paste a YouTube playlist URL','bad');
  $('#plPreviewPanel').innerHTML='<div class="empty">Reading YouTube playlist…</div>';

  try{
    playlistState.playlist=await api('/api/youtube/playlist',{method:'POST',body:JSON.stringify({url})});
    const entries=playlistState.playlist?.entries||[];
    playlistState.mappings=[];
    playlistState.mappingNotice='';

    if(playlistState.family==='series'){
      const selection=$('#plSeason')?.value||'';
      const onlyMissing=Boolean($('#plMissing')?.checked);
      const allTargets=orderedSeriesTargets(selection);

      /*
       * For All Seasons, exact SxxExx / Series x Episode y titles are safer
       * than positional mapping and naturally support playlists that start at
       * Season 3, skip seasons, or contain a non-contiguous subset.
       */
      if(selection==='all-regular'){
        const exact=exactPlaylistMappings(entries,allTargets,onlyMissing);
        if(entries.length&&exact.parsed===entries.length&&exact.matched>0){
          playlistState.mappings=exact.mappings;
          playlistState.targets=allTargets;
          playlistState.targetCount=allTargets.length;
          const minSeason=Math.min(...exact.parsedSeasons);
          const maxSeason=Math.max(...exact.parsedSeasons);
          playlistState.mappingNotice=`Detected explicit season/episode numbering in every playlist item. Mapping by episode token${Number.isFinite(minSeason)?` (Seasons ${minSeason}–${maxSeason})`:''}, not by playlist position.`;
          renderPlaylistPreview();
          return;
        }
      }

      const startSeason=Number($('#plStartSeason')?.value||regularPlaylistSeasons()[0]||1);
      const startEpisode=Math.max(1,Number($('#plStart')?.value||1));
      const targets=sequentialTargetsFromStart(selection,startSeason,startEpisode);
      playlistState.targets=targets;
      playlistState.targetCount=targets.length;
      const pairCount=Math.min(entries.length,targets.length);

      for(let i=0;i<pairCount;i++){
        const target=targets[i];
        playlistState.mappings.push({
          entry:entries[i],
          target,
          entryIndex:i,
          shouldQueue:!onlyMissing||(!youtubarrEpisodePresent(target)&&target.monitored!==false),
          detected:false,
        });
      }

      if(selection==='all-regular'){
        const parsedCount=entries.filter(entry=>parsePlaylistEpisodeToken(entry.title)).length;
        playlistState.mappingNotice=parsedCount
          ? `Only ${parsedCount} of ${entries.length} playlist titles had explicit season/episode numbering, so Youtubarr did not guess. Sequential mapping starts at S${String(startSeason).padStart(2,'0')}E${String(startEpisode).padStart(2,'0')}. Review the preview carefully.`
          : `Playlist titles do not expose reliable season/episode numbers. Sequential mapping starts at S${String(startSeason).padStart(2,'0')}E${String(startEpisode).padStart(2,'0')}. Change Start mapping at season/episode if this playlist begins later in the show.`;
      }
    }else{
      const start=Math.max(1,Number($('#plStart')?.value||1))-1;
      const tracks=[...(playlistState.allTargets||[])].sort((a,b)=>
        (Number(a.mediumNumber||1)-Number(b.mediumNumber||1))||
        (Number(a.trackNumber||a.absoluteTrackNumber||0)-Number(b.trackNumber||b.absoluteTrackNumber||0))
      ).slice(start);
      playlistState.targets=tracks;
      playlistState.targetCount=tracks.length;
      const pairCount=Math.min(entries.length,tracks.length);
      for(let i=0;i<pairCount;i++){
        playlistState.mappings.push({entry:entries[i],target:tracks[i],entryIndex:i,shouldQueue:true});
      }
    }

    renderPlaylistPreview();
  }catch(e){
    $('#plPreviewPanel').innerHTML=`<div class="error-box">${esc(e.message)}</div>`;
  }
}

const __v108RenderPlaylistPreview=window.renderPlaylistPreview;
window.renderPlaylistPreview=function(){
  __v108RenderPlaylistPreview();
  const panel=document.getElementById('plPreviewPanel');
  const notice=playlistState.mappingNotice;
  if(!panel||!notice)return;
  const summary=panel.querySelector('.playlist-summary');
  if(!summary)return;
  const info=document.createElement('div');
  info.className='context-banner playlist-mapping-notice';
  info.textContent=notice;
  summary.insertAdjacentElement('afterend',info);
};

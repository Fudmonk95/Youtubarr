/* Youtubarr v1.0.5 targeted fixes.
 * Loaded after the existing workflow scripts so these functions override the
 * older implementations without disturbing the Arr-style shell.
 */

async function queuePlaylistMappings(){
  const checks=$$('.plMapCheck:checked');
  if(!checks.length)return toast('Select at least one mapping','bad');

  let ok=0,failed=0;
  const errors=[];

  for(const c of checks){
    const i=Number(c.dataset.index);
    const p=playlistState.playlist.entries[i];
    const t=playlistState.targets[i];

    try{
      await api('/api/acquisitions',{
        method:'POST',
        body:JSON.stringify({
          kind:playlistState.family==='series'?'episode':'track',
          remoteId:Number(t.id),
          youtubeUrl:p.url,
        }),
      });
      ok++;
      c.closest('tr')?.classList.remove('mapping-failed');
      c.title='';
    }catch(e){
      failed++;
      const message=e?.message||String(e||'Unknown acquisition error');
      errors.push(message);
      c.closest('tr')?.classList.add('mapping-failed');
      c.title=message;
    }
  }

  let message=`${ok} mapped item${ok===1?'':'s'} queued`;
  if(failed){
    message+=`; ${failed} failed`;
    if(errors.length)message+=` — ${errors[0]}`;
  }
  toast(message,failed?'bad':'ok');
  if(ok)navigate('queue');
}

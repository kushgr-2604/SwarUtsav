import React, {useEffect, useRef, useState} from "react";

/** Optional device tests. No audio/screen media is saved or uploaded by this component. */
export default function DeviceCheck(){
 const [mic,setMic]=useState("not-tested");
 const [screen,setScreen]=useState("not-tested");
 const [message,setMessage]=useState("");
 const streams=useRef([]);
 const mounted=useRef(true);
 useEffect(()=>()=>{mounted.current=false; streams.current.forEach(s=>s.getTracks().forEach(t=>t.stop()));streams.current=[]},[]);
 async function testMicrophone(){
   if(!navigator.mediaDevices?.getUserMedia){
     setMic("unsupported");setMessage("Microphone testing needs HTTPS (or localhost) and a supported browser.");return;
   }
   setMic("testing");
   try{
     const stream=await navigator.mediaDevices.getUserMedia({audio:true,video:false});
     streams.current.push(stream);
     if(mounted.current){setMic("ready");setMessage("Microphone permission is working. Your audio was not saved.");}
     stream.getTracks().forEach(t=>t.stop());
     streams.current=streams.current.filter(s=>s!==stream);
   }catch(e){
     if(mounted.current){setMic("blocked");setMessage(e.name==="NotAllowedError"?"Microphone permission denied. Enable it in your browser's site settings.":"Microphone unavailable: "+e.message);}
   }
 }
 async function testScreen(){
   if(!navigator.mediaDevices?.getDisplayMedia){
     setScreen("unsupported");setMessage("Screen sharing requires a supported browser over HTTPS or localhost.");return;
   }
   setScreen("testing");
   try{
     // The user must choose a screen/window/tab in the native browser prompt.
     const stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:false});
     streams.current.push(stream);
     if(mounted.current){setScreen("ready");setMessage("Screen-sharing permission is working. No recording was saved.");}
     stream.getTracks().forEach(t=>t.stop());
     streams.current=streams.current.filter(s=>s!==stream);
   }catch(e){
     if(mounted.current){setScreen(e.name==="NotAllowedError"?"cancelled":"blocked");setMessage(e.name==="NotAllowedError"?"Screen selection was cancelled. Select a screen or tab when you start recording.":"Screen sharing unavailable: "+e.message);}
   }
 }
 const textFor=status=>({ready:"Ready ✓",testing:"Checking…",blocked:"Blocked",unsupported:"Unsupported",cancelled:"Not selected","not-tested":"Not tested"})[status]||status;
 return <section className="device-check" aria-label="Interview microphone and screen recording readiness">
   <div className="device-check-head"><div><strong>🎙 Microphone & 🖥 Screen recording</strong><p>Prepare your devices before starting. Recording controls will appear inside the AI interview studio.</p></div><span className="device-check-label">DEVICE CHECK</span></div>
   <div className="device-check-cards">
     <div className="device-check-card"><div><b>🎤 Microphone</b><span className={"device-status "+(mic==="ready"?"ready":"")}>{textFor(mic)}</span></div><p>For spoken answers and transcription. Click to test browser permission.</p><button type="button" onClick={testMicrophone} disabled={mic==="testing"}>Test microphone</button></div>
     <div className="device-check-card"><div><b>🖥 Screen share</b><span className={"device-status "+(screen==="ready"?"ready":"")}>{textFor(screen)}</span></div><p>For consent-based screen recording during the interview. You choose what to share.</p><button type="button" onClick={testScreen} disabled={screen==="testing"}>Test screen sharing</button></div>
   </div>
   {message&&<p className="device-check-message" role="status">{message}</p>}
   <p className="device-check-note">These checks never record or upload audio or your screen. Screen recording starts only after you consent and click Record screen in the interview.</p>
 </section>;
}

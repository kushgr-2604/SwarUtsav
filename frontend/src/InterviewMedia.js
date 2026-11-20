import React, {useEffect, useRef, useState} from "react";
// Browser-supported voice and optional, local-only screen capture.
export default function InterviewMedia({question,onTranscript}) {
  const [state,setState]=useState("");
  const [listening,setListening]=useState(false);
  const [capturing,setCapturing]=useState(false);
  const [consent,setConsent]=useState(false);
  const [url,setUrl]=useState("");
  const speech=useRef(null),stream=useRef(null),recorder=useRef(null),chunks=useRef([]),savedUrl=useRef("");
  const onTranscriptRef=useRef(onTranscript);
  useEffect(()=>{onTranscriptRef.current=onTranscript},[onTranscript]);
  function stopVoice(){window.speechSynthesis?.cancel()}
  function stopMic(){try{speech.current?.stop()}catch(_e){} speech.current=null;setListening(false)}
  function stopScreen(){if(recorder.current?.state==="recording")recorder.current.stop();stream.current?.getTracks().forEach(t=>t.stop());setCapturing(false)}
  useEffect(()=>()=>{try{speech.current?.abort()}catch(_e){}window.speechSynthesis?.cancel(); if(recorder.current?.state==="recording")recorder.current.stop();stream.current?.getTracks().forEach(t=>t.stop());if(savedUrl.current)URL.revokeObjectURL(savedUrl.current)},[]);
  useEffect(()=>{stopVoice();stopMic();stopScreen();setConsent(false)},[question]);
  function speak(){
    stopMic();stopVoice();
    if(!("speechSynthesis" in window)){setState("Voice playback unavailable in this browser.");return}
    const utterance=new SpeechSynthesisUtterance(question);utterance.lang="en-IN";utterance.rate=0.92;
    utterance.onerror=()=>setState("Voice playback failed. Please read the displayed question.");
    window.speechSynthesis.speak(utterance);setState("AI is speaking the question.");
  }
  function dictate(){
    const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!Recognition){setState("Dictation unsupported. You can type your answer.");return}
    stopVoice();stopMic();
    try {
      const r=new Recognition();r.lang="en-IN";r.continuous=true;r.interimResults=true;
      r.onresult=e=>{let transcript="";for(let i=0;i<e.results.length;i++)if(e.results[i].isFinal)transcript+=e.results[i][0].transcript+" ";onTranscriptRef.current?.(transcript.trim())};
      r.onerror=e=>{setListening(false);setState("Dictation error: "+e.error)};
      r.onend=()=>setListening(false);r.start();speech.current=r;setListening(true);setState("Listening to your answer.");
    } catch(e){setState("Microphone unavailable: "+e.message)}
  }
  async function capture(){
    if(!consent){setState("Consent to screen capture first.");return}
    if(!navigator.mediaDevices?.getDisplayMedia||!window.MediaRecorder){setState("Screen recording requires HTTPS/localhost and a supported browser.");return}
    try{
      const s=await navigator.mediaDevices.getDisplayMedia({video:true,audio:true});
      const mime=["video/webm;codecs=vp8,opus","video/webm"].find(t=>MediaRecorder.isTypeSupported(t));
      const r=new MediaRecorder(s,mime?{mimeType:mime}:undefined);chunks.current=[];stream.current=s;recorder.current=r;
      r.ondataavailable=e=>{if(e.data.size)chunks.current.push(e.data)};
      r.onstop=()=>{s.getTracks().forEach(t=>t.stop());if(savedUrl.current)URL.revokeObjectURL(savedUrl.current);savedUrl.current=URL.createObjectURL(new Blob(chunks.current,{type:r.mimeType||"video/webm"}));setUrl(savedUrl.current);setCapturing(false);setState("Local recording ready. Download it if needed.")};
      s.getVideoTracks()[0].addEventListener("ended",stopScreen,{once:true});
      r.start(1000);setCapturing(true);setState("Recording selected screen locally; not uploaded.");
    }catch(e){setState(e.name==="NotAllowedError"?"Screen sharing was cancelled.":e.message)}
  }
  return <div className="media-tools">
    <div className="media-buttons">
      <button type="button" className="text-button" onClick={speak}>🔊 Hear question</button>
      <button type="button" className="text-button" onClick={stopVoice}>Stop voice</button>
      <button type="button" className="text-button" onClick={listening?stopMic:dictate}>{listening?"⏹ Stop dictation":"🎙 Dictate answer"}</button>
    </div>
    <label className="media-consent"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> I consent to optional screen recording. Recording stays on my device unless I download it.</label>
    <div className="media-buttons">
      <button type="button" className="text-button" onClick={capturing?stopScreen:capture}>{capturing?"⏹ Stop screen recording":"⏺ Record my screen"}</button>
      {url&&<a className="text-button" href={url} download="swarutsav-screen.webm">Download recording</a>}
    </div>
    {state&&<p className="muted" role="status">{state}</p>}
  </div>;
}

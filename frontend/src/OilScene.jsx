import React, { useEffect } from 'react';
import { animated, useSpring } from '@react-spring/web';

export default function OilScene({paused}){
  const [styles,api]=useSpring(()=>({y:0,rotate:0,config:{mass:2,tension:60,friction:30}}));
  useEffect(()=>{
    const scroll=()=>api.start({y:paused?0:Math.min(window.scrollY*.1,38),rotate:paused?0:Math.min(window.scrollY*.004,2)});
    scroll();window.addEventListener('scroll',scroll,{passive:true});
    return ()=>window.removeEventListener('scroll',scroll);
  },[paused,api]);
  return <div className={`oil-scene ${paused?'motion-paused':''}`} aria-hidden="true">
    <animated.img style={styles} className="oil-bottle" src="/oil-hero.webp" alt="" />
    <div className="oil-fade" />
    <svg className="liquid-ribbon" viewBox="0 0 1100 380" preserveAspectRatio="none">
      <defs><linearGradient id="oil" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#fcebc2"/><stop offset=".23" stopColor="#bd8135"/><stop offset=".5" stopColor="#efc879"/><stop offset=".85" stopColor="#5d3b13"/><stop offset="1" stopColor="#c88932"/></linearGradient></defs>
      <path className="ribbon-highlight" d="M1100 -80C830 100 1090 250 990 340S730 270 850 210" fill="none" stroke="url(#oil)" strokeWidth="2" opacity=".5"/>
    </svg>
    <span className="oil-drop drop-one"/><span className="oil-drop drop-two"/>
  </div>;
}

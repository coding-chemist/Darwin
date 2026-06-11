import React from 'react';

/**
 * Darwin logo — exact phylogenetic tree from coding-chemist portfolio card.
 * Root node at bottom → two splits → four terminal nodes at top.
 */
export default function DarwinLogo({ size = 32, color = '#059669', className = '' }) {
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 22 22" fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Darwin logo"
    >
      <line x1="11" y1="20"   x2="11" y2="12.5" stroke={color} strokeWidth="1.4" strokeLinecap="round"/>
      <line x1="11" y1="12.5" x2="5"  y2="8.5"  stroke={color} strokeWidth="1.2" strokeLinecap="round"/>
      <line x1="11" y1="12.5" x2="17" y2="8.5"  stroke={color} strokeWidth="1.2" strokeLinecap="round"/>
      <line x1="5"  y1="8.5"  x2="2.5" y2="4.5" stroke={color} strokeWidth="1"   strokeLinecap="round"/>
      <line x1="5"  y1="8.5"  x2="7.5" y2="4.5" stroke={color} strokeWidth="1"   strokeLinecap="round"/>
      <line x1="17" y1="8.5"  x2="14.5" y2="4.5" stroke={color} strokeWidth="1"  strokeLinecap="round"/>
      <line x1="17" y1="8.5"  x2="19.5" y2="4.5" stroke={color} strokeWidth="1"  strokeLinecap="round"/>
      <circle cx="2.5"  cy="4"    r="1.3" fill={color}/>
      <circle cx="7.5"  cy="4"    r="1.3" fill={color}/>
      <circle cx="14.5" cy="4"    r="1.3" fill={color}/>
      <circle cx="19.5" cy="4"    r="1.3" fill={color}/>
      <circle cx="11"   cy="20.3" r="1.5" fill={color}/>
    </svg>
  );
}

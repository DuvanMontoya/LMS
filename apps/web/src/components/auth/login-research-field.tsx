const equations = [
  {
    className: 'is-riemann',
    formula: 'ζ(s) = 0,  Re(s) = ½',
    label: 'Hipótesis de Riemann',
  },
  {
    className: 'is-navier-stokes',
    formula: '∂ₜu + (u · ∇)u = −∇p + νΔu',
    label: 'Navier–Stokes',
  },
  {
    className: 'is-yang-mills',
    formula: 'DμFμν = 0',
    label: 'Yang–Mills',
  },
  {
    className: 'is-hodge',
    formula: 'Hᵖ,ᵖ(X) ∩ H²ᵖ(X, ℚ)',
    label: 'Conjetura de Hodge',
  },
  {
    className: 'is-bsd',
    formula: 'rank E(ℚ) = ordₛ₌₁ L(E, s)',
    label: 'Birch–Swinnerton-Dyer',
  },
  {
    className: 'is-p-np',
    formula: 'P ≟ NP',
    label: 'P versus NP',
  },
  {
    className: 'is-poincare',
    formula: 'π₁(M) = 0  ⟹  M ≃ S³',
    label: 'Conjetura de Poincaré',
  },
] as const;

export function LoginResearchField() {
  return (
    <div className="login-research-field" aria-hidden="true">
      <svg
        className="login-research-field__geometry"
        viewBox="0 0 1600 1000"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <pattern
            id="login-grid"
            width="80"
            height="80"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M80 0H0V80"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
            />
          </pattern>
          <linearGradient id="login-curve" x1="0" x2="1">
            <stop stopColor="#1d252d" stopOpacity=".04" />
            <stop offset=".5" stopColor="#1d252d" stopOpacity=".42" />
            <stop offset="1" stopColor="#1d252d" stopOpacity=".04" />
          </linearGradient>
        </defs>
        <rect
          width="1600"
          height="1000"
          fill="url(#login-grid)"
          opacity=".75"
        />
        <g fill="none" stroke="url(#login-curve)" strokeWidth="1.25">
          <path d="M-80 288C120 120 270 425 500 290S850 110 1080 286s335 160 610-75" />
          <path d="M-100 738C120 515 295 820 530 676s392-152 630 26 320 131 545-82" />
          <path d="M900-35c105 43 190 132 196 256 8 157-109 293-267 302-155 9-293-111-302-267-9-158 110-293 267-302 37-2 73 3 106 11Z" />
          <path d="M952 4c78 55 126 146 113 247-18 139-145 239-284 221-140-17-240-144-222-284 18-139 145-238 284-221 41 5 78 20 109 37Z" />
          <path d="M1092 633c-154-42-262 57-231 174 33 125 197 172 323 89 103-67 162-173 252-153 73 16 88 106 133 163" />
        </g>
        <g fill="none" stroke="#1f2931" strokeOpacity=".18">
          <path d="M158 548c52-235 153-233 205 0s151 236 205 0 151-235 205 0" />
          <path d="M154 548h620M464 277v470" strokeDasharray="4 8" />
        </g>
        <g fill="#242d35" opacity=".28">
          <circle cx="464" cy="548" r="5" />
          <circle cx="926" cy="286" r="4" />
          <circle cx="1093" cy="633" r="4" />
        </g>
      </svg>
      {equations.map((equation) => (
        <div
          className={`login-research-field__equation ${equation.className}`}
          key={equation.className}
        >
          <span className="login-research-field__formula">
            {equation.formula}
          </span>
          <span>{equation.label}</span>
        </div>
      ))}
    </div>
  );
}

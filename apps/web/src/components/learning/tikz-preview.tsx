import { Code2, Shapes } from 'lucide-react';

type Point = { x: number; y: number };
type TikzPrimitive =
  | {
      color: string;
      dashed: boolean;
      kind: 'path';
      points: Point[];
      width: number;
    }
  | {
      color: string;
      fill: string;
      kind: 'circle';
      point: Point;
      radius: number;
      width: number;
    }
  | { kind: 'label'; point: Point; text: string };

const COLOR_MAP: Record<string, string> = {
  black: '#0f172a',
  blue: '#2563eb',
  brown: '#92400e',
  cyan: '#0891b2',
  gray: '#64748b',
  green: '#059669',
  orange: '#ea580c',
  purple: '#7c3aed',
  red: '#dc2626',
  teal: '#0f766e',
  violet: '#7c3aed',
};

export function parseTikzPreview(source: string) {
  const primitives: TikzPrimitive[] = [];
  let supportedStatements = 0;
  const statements = source.replace(/%[^\n]*/g, '').split(';');
  for (const statement of statements) {
    const command = statement.trim();
    if (!command) continue;
    const options =
      command.match(/\\(?:draw|fill|filldraw)\s*\[([^\]]*)\]/)?.[1] ?? '';
    const color = tikzColor(options);
    const width = /(?:very\s+thick|ultra\s+thick)/.test(options)
      ? 3
      : /thick/.test(options)
        ? 2
        : 1.35;
    const circle = command.match(
      /\((-?\d*\.?\d+),\s*(-?\d*\.?\d+)\)\s*circle\s*\((-?\d*\.?\d+)(?:cm)?\)/,
    );
    if (circle) {
      primitives.push({
        color,
        fill: /\\(?:fill|filldraw)/.test(command) ? color : 'none',
        kind: 'circle',
        point: { x: Number(circle[1]), y: Number(circle[2]) },
        radius: Math.abs(Number(circle[3])),
        width,
      });
      supportedStatements += 1;
      continue;
    }
    const node = command.match(
      /\\node(?:\[[^\]]*\])?\s*at\s*\((-?\d*\.?\d+),\s*(-?\d*\.?\d+)\)\s*\{([\s\S]{1,240})\}$/,
    );
    if (node) {
      primitives.push({
        kind: 'label',
        point: { x: Number(node[1]), y: Number(node[2]) },
        text: readableTikzLabel(node[3] ?? ''),
      });
      supportedStatements += 1;
      continue;
    }
    if (!/\\(?:draw|fill|filldraw)/.test(command)) continue;
    const points = [
      ...command.matchAll(/\((-?\d*\.?\d+),\s*(-?\d*\.?\d+)\)/g),
    ].map((match) => ({ x: Number(match[1]), y: Number(match[2]) }));
    if (points.length >= 2) {
      primitives.push({
        color,
        dashed: /dashed|dotted/.test(options),
        kind: 'path',
        points,
        width,
      });
      supportedStatements += 1;
    }
  }
  return { primitives, supportedStatements };
}

export function TikzPreview({
  caption,
  source,
}: Readonly<{ caption: string; source: string }>) {
  const parsed = parseTikzPreview(source);
  const points = parsed.primitives.flatMap((primitive) =>
    primitive.kind === 'path' ? primitive.points : [primitive.point],
  );
  const bounds = coordinateBounds(points);
  return (
    <figure className="source-tikz-preview">
      <header>
        <div>
          <Shapes />
          <span>
            <strong>{caption}</strong>
            <small>Vista vectorial segura en el navegador</small>
          </span>
        </div>
        <span>{parsed.supportedStatements} trazos interpretados</span>
      </header>
      {points.length && bounds ? (
        <svg
          aria-label={caption}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          viewBox="0 0 800 480"
        >
          <rect fill="#ffffff" height="480" rx="18" width="800" />
          {parsed.primitives.map((primitive, index) => {
            if (primitive.kind === 'path')
              return (
                <polyline
                  fill="none"
                  key={index}
                  points={primitive.points
                    .map((point) => mapPoint(point, bounds))
                    .map((point) => `${point.x},${point.y}`)
                    .join(' ')}
                  stroke={primitive.color}
                  strokeDasharray={primitive.dashed ? '8 7' : undefined}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={primitive.width}
                />
              );
            const point = mapPoint(primitive.point, bounds);
            if (primitive.kind === 'circle')
              return (
                <circle
                  cx={point.x}
                  cy={point.y}
                  fill={primitive.fill}
                  key={index}
                  r={Math.max(3, (primitive.radius / bounds.span) * 560)}
                  stroke={primitive.color}
                  strokeWidth={primitive.width}
                />
              );
            return (
              <text
                fill="#334155"
                fontFamily="ui-sans-serif, system-ui, sans-serif"
                fontSize="13"
                key={index}
                textAnchor="middle"
                x={point.x}
                y={point.y}
              >
                {primitive.text}
              </text>
            );
          })}
        </svg>
      ) : (
        <div className="source-tikz-preview__unsupported">
          <Shapes />
          <p>
            Esta figura usa instrucciones TikZ avanzadas que no pueden
            proyectarse sin ejecutar un compilador TeX.
          </p>
        </div>
      )}
      <details>
        <summary>
          <Code2 /> Ver fuente TikZ preservada
        </summary>
        <pre>
          <code>{source}</code>
        </pre>
      </details>
    </figure>
  );
}

function tikzColor(options: string) {
  const explicit = Object.keys(COLOR_MAP).find((name) =>
    new RegExp(`(?:^|[,=])\\s*${name}(?:!\\d+)?(?:,|$)`).test(options),
  );
  return COLOR_MAP[explicit ?? 'black'] ?? COLOR_MAP.black!;
}

function readableTikzLabel(value: string) {
  return value
    .replace(/\$+/g, '')
    .replace(/\\(?:textbf|textit|mathrm|mathbf)\{([^{}]*)\}/g, '$1')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[{}]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 80);
}

function coordinateBounds(points: Point[]) {
  if (!points.length) return null;
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return {
    minX,
    minY,
    span: Math.max(maxX - minX, maxY - minY, 1),
  };
}

function mapPoint(
  point: Point,
  bounds: NonNullable<ReturnType<typeof coordinateBounds>>,
) {
  const padding = 42;
  const scale = (480 - padding * 2) / bounds.span;
  return {
    x: padding + (point.x - bounds.minX) * scale,
    y: 480 - padding - (point.y - bounds.minY) * scale,
  };
}

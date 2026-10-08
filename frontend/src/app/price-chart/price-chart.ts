import {
  afterRenderEffect,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  input,
  viewChild,
} from '@angular/core';
import {
  Chart,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
  type ChartDataset,
  type Plugin,
} from 'chart.js';
import { money } from '../products';

Chart.register(LineController, LineElement, PointElement, LinearScale, Tooltip);

export interface Series {
  label: string;
  color: string;
  currency: string | null;
  points: { x: number; y: number }[];
}

type LineDataset = ChartDataset<'line', { x: number; y: number }[]>;

const SURFACE = '#151b20';
const GRID = '#222b31';
const MUTED = '#8a9aa6';

const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const longDate = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
});

const DRAW_MS = 900;
const ERASE_MS = 300;

interface Wipe {
  start: number;
  ms: number;
  drawing: boolean;
}
const wipes = new WeakMap<object, Wipe>();

function shownFraction(ds: object, now: number): number {
  const wipe = wipes.get(ds);
  if (!wipe) return 1;
  const t = Math.min((now - wipe.start) / wipe.ms, 1);
  return wipe.drawing ? t : 1 - t;
}

// Turning around mid-wipe continues from the current edge instead of jumping.
function steer(ds: object, drawing: boolean, now: number): void {
  if ((wipes.get(ds)?.drawing ?? true) === drawing) return;
  const shown = shownFraction(ds, now);
  const ms = drawing ? DRAW_MS : ERASE_MS;
  wipes.set(ds, { start: now - (drawing ? shown : 1 - shown) * ms, ms, drawing });
}

const reveal: Plugin<'line'> = {
  id: 'reveal',
  beforeDatasetDraw(chart, { index }) {
    const ds = chart.data.datasets[index];
    if (!wipes.has(ds)) return;
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.beginPath();
    ctx.rect(
      0,
      0,
      chartArea.left + chartArea.width * shownFraction(ds, performance.now()),
      chart.height,
    );
    ctx.clip();
  },
  afterDatasetDraw(chart, { index }) {
    if (wipes.has(chart.data.datasets[index])) chart.ctx.restore();
  },
};

const crosshair: Plugin<'line'> = {
  id: 'crosshair',
  afterDatasetsDraw(chart) {
    const [active] = chart.tooltip?.getActiveElements() ?? [];
    if (!active) return;
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.strokeStyle = '#5f788a';
    ctx.beginPath();
    ctx.moveTo(active.element.x, chartArea.top);
    ctx.lineTo(active.element.x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

@Component({
  selector: 'app-price-chart',
  template: `
    <div class="frame">
      <canvas #canvas role="img" [attr.aria-label]="'Price history for ' + labels()"></canvas>
      @if (!series().length) {
        <p class="empty">Tick products in the sidebar or in Customize to chart them.</p>
      }
    </div>
    <ul class="legend" aria-label="Legend">
      @for (s of series(); track s.label) {
        <li>
          <span class="key" [style.background]="s.color"></span
          ><span class="label">{{ s.label }}</span>
        </li>
      }
    </ul>
  `,
  styles: `
    .frame {
      position: relative;
      height: 22rem;
    }
    .empty {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      margin: 0;
      color: var(--muted);
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem 1.25rem;
      margin: 1rem 0 0;
      padding: 0;
      list-style: none;
      font-size: 0.8rem;
      color: var(--ink-2);
    }
    .legend li {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      min-width: 0;
      max-width: min(22rem, 100%);
    }
    .label {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .key {
      flex: none;
      width: 14px;
      height: 2px;
      border-radius: 1px;
    }
  `,
})
export class PriceChart {
  readonly series = input.required<Series[]>();
  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');

  protected readonly labels = computed(() =>
    this.series()
      .map((s) => s.label)
      .join(', '),
  );

  constructor() {
    let chart: Chart<'line', { x: number; y: number }[]> | undefined;
    const reduceMotion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    let frame = 0;

    const tick = () => {
      if (!chart) return;
      const now = performance.now();
      const before = chart.data.datasets.length;
      chart.data.datasets = chart.data.datasets.filter((ds) => {
        const wipe = wipes.get(ds);
        if (!wipe || now - wipe.start < wipe.ms) return true;
        wipes.delete(ds);
        return wipe.drawing;
      });
      if (chart.data.datasets.length < before) chart.update();
      else chart.draw();
      frame = chart.data.datasets.some((ds) => wipes.has(ds)) ? requestAnimationFrame(tick) : 0;
    };

    // One shared axis can only carry a currency symbol when every line uses it
    let axisCurrency: string | null = null;
    const currencyOf = new Map<string, string | null>();

    afterRenderEffect(() => {
      chart ??= new Chart(this.canvas().nativeElement, {
        type: 'line',
        data: { datasets: [] },
        plugins: [reveal, crosshair],
        options: {
          maintainAspectRatio: false,
          animation: reduceMotion ? false : { duration: 300 },
          interaction: { mode: 'nearest', axis: 'x', intersect: false },
          font: { family: 'system-ui, -apple-system, "Segoe UI", sans-serif' },
          scales: {
            x: {
              type: 'linear',
              grid: { color: GRID },
              border: { color: GRID },
              ticks: {
                color: MUTED,
                maxTicksLimit: 8,
                callback: (v) => shortDate.format(Number(v)),
              },
            },
            y: {
              grid: { color: GRID },
              border: { display: false },
              ticks: { color: MUTED, callback: (v) => money(Number(v), axisCurrency) },
            },
          },
          plugins: {
            tooltip: {
              backgroundColor: 'rgb(13 18 21 / 0.95)',
              borderColor: 'rgb(203 213 219 / 0.15)',
              borderWidth: 1,
              padding: 10,
              titleColor: '#cbd5db',
              bodyColor: '#f1f4f6',
              usePointStyle: true,
              itemSort: (a, b) => (b.parsed.y ?? 0) - (a.parsed.y ?? 0),
              callbacks: {
                title: ([item]) => (item ? longDate.format(item.parsed.x ?? 0) : ''),
                label: (item) =>
                  `${money(item.parsed.y ?? 0, currencyOf.get(item.dataset.label ?? '') ?? null)}  ${item.dataset.label}`,
                labelPointStyle: () => ({ pointStyle: 'line', rotation: 0 }),
              },
            },
          },
        },
      });

      const series = this.series();
      const currencies = new Set(series.map((s) => s.currency));
      axisCurrency = currencies.size === 1 ? [...currencies][0] : null;
      for (const s of series) currencyOf.set(s.label, s.currency);

      const now = performance.now();
      const leaving = new Map(chart.data.datasets.map((ds) => [ds.label, ds]));
      const fresh: LineDataset[] = [];
      const datasets = series.map((s) => {
        let ds = leaving.get(s.label);
        leaving.delete(s.label);
        if (ds) {
          if (!reduceMotion) steer(ds, true, now);
        } else {
          // Skips Chart.js's grow-from-baseline intro so the wipe is the only entrance.
          ds = {
            label: s.label,
            data: [],
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: SURFACE,
            animation: false,
          };
          fresh.push(ds);
          if (!reduceMotion) wipes.set(ds, { start: now, ms: DRAW_MS, drawing: true });
        }
        ds.data = s.points;
        ds.borderColor = ds.backgroundColor = s.color;
        return ds;
      });
      if (!reduceMotion) {
        for (const ds of leaving.values()) {
          steer(ds, false, now);
          datasets.push(ds);
        }
      }

      chart.data.datasets = datasets;
      chart.update();
      for (const ds of fresh) delete ds.animation;
      cancelAnimationFrame(frame);
      tick();
    });

    inject(DestroyRef).onDestroy(() => {
      cancelAnimationFrame(frame);
      chart?.destroy();
    });
  }
}

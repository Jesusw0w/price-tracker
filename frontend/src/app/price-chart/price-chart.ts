import { afterRenderEffect, Component, DestroyRef, ElementRef, inject, input, viewChild } from '@angular/core';
import { Chart, LinearScale, LineController, LineElement, PointElement, Tooltip, type Plugin } from 'chart.js';
import { eur } from '../products';

Chart.register(LineController, LineElement, PointElement, LinearScale, Tooltip);

export interface Series {
  label: string;
  color: string;
  points: { x: number; y: number }[];
}

const SURFACE = '#151b20';
const GRID = '#222b31';
const MUTED = '#8a9aa6';

const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const longDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

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
        <p class="empty">Tick products in the sidebar to chart them.</p>
      }
    </div>
    <ul class="legend" aria-label="Legend">
      @for (s of series(); track s.label) {
        <li><span class="key" [style.background]="s.color"></span><span class="label">{{ s.label }}</span></li>
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

  protected labels(): string {
    return this.series()
      .map((s) => s.label)
      .join(', ');
  }

  constructor() {
    let chart: Chart<'line', { x: number; y: number }[]> | undefined;
    const reduceMotion = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    afterRenderEffect(() => {
      const datasets = this.series().map((s) => ({
        label: s.label,
        data: s.points,
        borderColor: s.color,
        backgroundColor: s.color,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBorderWidth: 2,
        pointHoverBorderColor: SURFACE,
      }));

      if (chart) {
        chart.data.datasets = datasets;
        chart.update();
        return;
      }

      chart = new Chart(this.canvas().nativeElement, {
        type: 'line',
        data: { datasets },
        plugins: [crosshair],
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
              ticks: { color: MUTED, maxTicksLimit: 8, callback: (v) => shortDate.format(Number(v)) },
            },
            y: {
              grid: { color: GRID },
              border: { display: false },
              ticks: { color: MUTED, callback: (v) => eur(Number(v)) },
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
                label: (item) => `${eur(item.parsed.y ?? 0)}  ${item.dataset.label}`,
                labelPointStyle: () => ({ pointStyle: 'line', rotation: 0 }),
              },
            },
          },
        },
      });
    });

    inject(DestroyRef).onDestroy(() => chart?.destroy());
  }
}

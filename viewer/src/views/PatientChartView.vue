<script setup lang="ts">
import { computed, watchEffect } from 'vue';
import { storeToRefs } from 'pinia';
import { useFhirStore } from '@/stores/fhir';
import type { FhirResource } from '@/api/fhir';

const props = defineProps<{ id: string }>();
const store = useFhirStore();
const { charts, loadingChart, error } = storeToRefs(store);

watchEffect(() => {
  store.loadChart(props.id);
});

const chart = computed(() => charts.value[props.id]);

function displayName(patient: FhirResource | undefined): string {
  if (!patient) return '—';
  const names = patient.name as Array<Record<string, unknown>> | undefined;
  const first = names?.[0];
  if (!first) return '—';
  const family = first.family as string | undefined;
  const given = (first.given as string[] | undefined)?.join(' ') ?? '';
  return [given, family].filter(Boolean).join(' ') || '—';
}

function patientField(patient: FhirResource | undefined, key: string): string {
  if (!patient) return '—';
  const value = patient[key];
  return typeof value === 'string' && value ? value : '—';
}

function patientMrn(patient: FhirResource | undefined): string {
  if (!patient) return '—';
  const ids = patient.identifier as Array<Record<string, unknown>> | undefined;
  return (ids?.[0]?.value as string | undefined) ?? '—';
}

function encounterClass(enc: FhirResource): string {
  const klass = enc.class as Record<string, unknown> | undefined;
  return (klass?.display as string | undefined) ?? (klass?.code as string | undefined) ?? '—';
}

function encounterDates(enc: FhirResource): string {
  const period = enc.period as Record<string, string> | undefined;
  if (!period) return '—';
  const start = period.start ? new Date(period.start).toLocaleString() : '—';
  const end = period.end ? new Date(period.end).toLocaleString() : '(ongoing)';
  return `${start} → ${end}`;
}

interface ReportRow {
  id: string | undefined;
  status: string;
  code: string;
  display: string;
  effective: string;
}

function flattenReports(reports: FhirResource[]): ReportRow[] {
  return reports.map((r) => {
    const coding = (r.code as Record<string, unknown> | undefined)?.coding as
      | Array<Record<string, unknown>>
      | undefined;
    const first = coding?.[0];
    return {
      id: r.id,
      status: (r.status as string | undefined) ?? '—',
      code: (first?.code as string | undefined) ?? '',
      display: (first?.display as string | undefined) ?? '',
      effective: (r.effectiveDateTime as string | undefined) ?? '',
    };
  });
}

interface ObsRow {
  code: string;
  display: string;
  value: string;
  unit: string;
  range: string;
  interpretation: string;
  effective: string;
}

function flattenObservations(observations: FhirResource[]): ObsRow[] {
  return observations.map((o) => {
    const code = o.code as Record<string, unknown> | undefined;
    const coding = (code?.coding as Array<Record<string, unknown>> | undefined)?.[0] ?? {};
    const valueQty = o.valueQuantity as Record<string, unknown> | undefined;
    const valueStr = o.valueString as string | undefined;
    const range = (o.referenceRange as Array<Record<string, unknown>> | undefined)?.[0];
    const interp = (o.interpretation as Array<Record<string, unknown>> | undefined)?.[0];
    const interpCoding = (interp?.coding as Array<Record<string, unknown>> | undefined)?.[0];
    return {
      code: (coding.code as string | undefined) ?? '—',
      display: (coding.display as string | undefined) ?? '',
      value: valueQty ? `${valueQty.value ?? ''}`.trim() : (valueStr ?? '—'),
      unit: (valueQty?.unit as string | undefined) ?? '',
      range: (range?.text as string | undefined) ?? '',
      interpretation: (interpCoding?.code as string | undefined) ?? '',
      effective: (o.effectiveDateTime as string | undefined) ?? '',
    };
  });
}
</script>

<template>
  <section>
    <router-link to="/patients" class="muted">← Patients</router-link>

    <div v-if="loadingChart && !chart" class="card">
      <p class="muted">Loading chart…</p>
    </div>

    <div v-if="error" class="card">
      <p class="muted">{{ error }}</p>
    </div>

    <template v-if="chart">
      <h1>{{ displayName(chart.patient) }}</h1>
      <div class="demographics card">
        <div>
          <span class="muted">MRN</span><span class="mono">{{ patientMrn(chart.patient) }}</span>
        </div>
        <div>
          <span class="muted">Sex</span><span>{{ patientField(chart.patient, 'gender') }}</span>
        </div>
        <div>
          <span class="muted">DOB</span
          ><span class="mono">{{ patientField(chart.patient, 'birthDate') }}</span>
        </div>
        <div>
          <span class="muted">FHIR ID</span><span class="mono">{{ chart.patient.id }}</span>
        </div>
      </div>

      <div class="card">
        <h2>Encounters</h2>
        <table v-if="chart.encounters.length">
          <thead>
            <tr>
              <th>Class</th>
              <th>Status</th>
              <th>Period</th>
              <th>FHIR ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in chart.encounters" :key="e.id">
              <td>{{ encounterClass(e) }}</td>
              <td>
                <span class="chip">{{ e.status }}</span>
              </td>
              <td class="mono">{{ encounterDates(e) }}</td>
              <td class="mono muted">{{ e.id }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No encounters recorded.</p>
      </div>

      <div class="card">
        <h2>Diagnostic reports</h2>
        <ul v-if="chart.reports.length" class="report-list">
          <li v-for="r in flattenReports(chart.reports)" :key="r.id">
            <span class="chip">{{ r.status }}</span>
            <span class="report-code mono">{{ r.code }}</span>
            <span>{{ r.display }}</span>
            <span class="muted mono">{{ r.effective }}</span>
          </li>
        </ul>
        <p v-else class="muted">No diagnostic reports.</p>
      </div>

      <div class="card">
        <h2>Observations</h2>
        <table v-if="chart.observations.length">
          <thead>
            <tr>
              <th>LOINC</th>
              <th>Name</th>
              <th>Value</th>
              <th>Unit</th>
              <th>Range</th>
              <th>Flag</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in flattenObservations(chart.observations)" :key="i">
              <td class="mono">{{ row.code }}</td>
              <td>{{ row.display }}</td>
              <td class="mono">{{ row.value }}</td>
              <td>{{ row.unit }}</td>
              <td class="mono">{{ row.range }}</td>
              <td>
                <span
                  v-if="row.interpretation"
                  class="chip"
                  :class="row.interpretation === 'N' ? 'ok' : 'warn'"
                >
                  {{ row.interpretation }}
                </span>
              </td>
              <td class="mono muted">{{ row.effective }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="muted">No observations.</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.demographics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}
.demographics > div {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.demographics .muted {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
@media (max-width: 720px) {
  .demographics {
    grid-template-columns: repeat(2, 1fr);
  }
}
.report-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.9rem;
}
.report-list li {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.report-code {
  font-weight: 600;
}
</style>

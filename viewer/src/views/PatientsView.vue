<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useFhirStore } from '@/stores/fhir';
import type { FhirResource } from '@/api/fhir';

const router = useRouter();
const store = useFhirStore();
const { patients, loadingList, error } = storeToRefs(store);

onMounted(() => {
  store.loadPatients();
});

function displayName(patient: FhirResource): string {
  const names = patient.name as Array<Record<string, unknown>> | undefined;
  const first = names?.[0];
  if (!first) return '—';
  const family = first.family as string | undefined;
  const given = (first.given as string[] | undefined)?.join(' ') ?? '';
  return [given, family].filter(Boolean).join(' ') || '—';
}

function mrn(patient: FhirResource): string {
  const ids = patient.identifier as Array<Record<string, unknown>> | undefined;
  const first = ids?.[0];
  return (first?.value as string | undefined) ?? '—';
}

function gender(patient: FhirResource): string {
  return (patient.gender as string | undefined) ?? '—';
}

function dob(patient: FhirResource): string {
  return (patient.birthDate as string | undefined) ?? '—';
}

function openPatient(id: string | undefined) {
  if (id) router.push({ name: 'patient', params: { id } });
}
</script>

<template>
  <section>
    <h1>Patients</h1>
    <p class="muted">Patients persisted to the FHIR server. Click for the clinical chart.</p>

    <div class="card" style="padding: 0">
      <table v-if="patients.length">
        <thead>
          <tr>
            <th>Name</th>
            <th>MRN</th>
            <th>Sex</th>
            <th>DOB</th>
            <th>ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in patients" :key="p.id" class="clickable" @click="openPatient(p.id)">
            <td>{{ displayName(p) }}</td>
            <td class="mono">{{ mrn(p) }}</td>
            <td>{{ gender(p) }}</td>
            <td class="mono">{{ dob(p) }}</td>
            <td class="mono muted">{{ p.id }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else-if="loadingList" style="padding: 2rem; text-align: center" class="muted">
        Loading…
      </p>
      <p v-else-if="error" style="padding: 2rem; text-align: center" class="muted">
        {{ error }}
      </p>
      <p v-else style="padding: 2rem; text-align: center" class="muted">
        No patients in the FHIR server yet.
      </p>
    </div>
  </section>
</template>

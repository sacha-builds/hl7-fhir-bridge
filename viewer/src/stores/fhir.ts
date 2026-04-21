import { defineStore } from 'pinia';
import {
  entriesOf,
  getPatient,
  searchDiagnosticReportsForPatient,
  searchEncountersForPatient,
  searchObservationsForPatient,
  searchPatients,
  type FhirResource,
} from '@/api/fhir';

interface PatientChart {
  patient: FhirResource;
  encounters: FhirResource[];
  observations: FhirResource[];
  reports: FhirResource[];
}

interface State {
  patients: FhirResource[];
  charts: Record<string, PatientChart>;
  loadingList: boolean;
  loadingChart: boolean;
  error: string | null;
}

export const useFhirStore = defineStore('fhir', {
  state: (): State => ({
    patients: [],
    charts: {},
    loadingList: false,
    loadingChart: false,
    error: null,
  }),

  actions: {
    async loadPatients(): Promise<void> {
      this.loadingList = true;
      this.error = null;
      try {
        const bundle = await searchPatients(50);
        this.patients = entriesOf(bundle);
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'failed to load patients';
      } finally {
        this.loadingList = false;
      }
    },

    async loadChart(patientId: string): Promise<void> {
      this.loadingChart = true;
      this.error = null;
      try {
        const [patient, enc, obs, reports] = await Promise.all([
          getPatient(patientId),
          searchEncountersForPatient(patientId),
          searchObservationsForPatient(patientId),
          searchDiagnosticReportsForPatient(patientId),
        ]);
        this.charts[patientId] = {
          patient,
          encounters: entriesOf(enc),
          observations: entriesOf(obs),
          reports: entriesOf(reports),
        };
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'failed to load chart';
      } finally {
        this.loadingChart = false;
      }
    },
  },
});

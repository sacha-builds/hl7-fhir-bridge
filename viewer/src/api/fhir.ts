export interface FhirResource {
  resourceType: string;
  id?: string;
  [key: string]: unknown;
}

export interface FhirBundle {
  resourceType: 'Bundle';
  type: string;
  total?: number;
  entry?: Array<{ resource: FhirResource }>;
}

const BASE = import.meta.env.VITE_BRIDGE_API_URL ?? 'http://localhost:8000';

function url(path: string, params?: Record<string, string>): string {
  const u = new URL(`${BASE}/fhir/${path.replace(/^\//, '')}`);
  if (params) for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  return u.toString();
}

async function fetchJson<T>(u: string): Promise<T> {
  const response = await fetch(u, {
    headers: { Accept: 'application/fhir+json' },
  });
  if (!response.ok) throw new Error(`fhir fetch ${u} failed: ${response.status}`);
  return (await response.json()) as T;
}

export function searchPatients(count = 50): Promise<FhirBundle> {
  return fetchJson(url('Patient', { _count: String(count), _sort: '-_lastUpdated' }));
}

export function getPatient(id: string): Promise<FhirResource> {
  return fetchJson(url(`Patient/${id}`));
}

export function searchEncountersForPatient(patientId: string): Promise<FhirBundle> {
  return fetchJson(url('Encounter', { subject: `Patient/${patientId}`, _count: '50' }));
}

export function searchObservationsForPatient(patientId: string): Promise<FhirBundle> {
  return fetchJson(
    url('Observation', {
      subject: `Patient/${patientId}`,
      _count: '100',
      _sort: '-date',
    }),
  );
}

export function searchDiagnosticReportsForPatient(patientId: string): Promise<FhirBundle> {
  return fetchJson(
    url('DiagnosticReport', {
      subject: `Patient/${patientId}`,
      _count: '50',
      _sort: '-date',
    }),
  );
}

export function entriesOf(bundle: FhirBundle): FhirResource[] {
  return bundle.entry?.map((e) => e.resource) ?? [];
}

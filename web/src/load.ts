/** Fetches a JSON file and returns it unparsed-checked; callers validate the shape. */
export async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load ${url} (HTTP ${response.status}). Run "npm run prepare-data" in web/.`);
  }
  return response.json();
}

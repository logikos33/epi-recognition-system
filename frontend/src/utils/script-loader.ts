/**
 * Utility to load scripts dynamically
 * Useful for loading external libraries like hls.js on demand
 */

const loadedScripts = new Set<string>();

export function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    // Return immediately if already loaded
    if (loadedScripts.has(src)) {
      resolve();
      return;
    }

    // Check if script already exists in DOM
    const existingScript = document.querySelector(`script[src="${src}"]`);
    if (existingScript) {
      loadedScripts.add(src);
      resolve();
      return;
    }

    // Create and load script
    const script = document.createElement('script');
    script.src = src;
    script.async = true;

    script.onload = () => {
      loadedScripts.add(src);
      resolve();
    };

    script.onerror = () => {
      reject(new Error(`Failed to load script: ${src}`));
    };

    document.head.appendChild(script);
  });
}

export function isScriptLoaded(src: string): boolean {
  return loadedScripts.has(src) ||
         document.querySelector(`script[src="${src}"]`) !== null;
}

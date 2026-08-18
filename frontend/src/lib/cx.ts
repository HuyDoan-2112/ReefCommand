/**
 * Join class names, dropping anything falsy.
 *
 * `tsconfig.json` sets `noUncheckedIndexedAccess`, so a CSS module lookup is
 * typed `string | undefined` even when the class certainly exists. That strict
 * setting is worth keeping, so class names are composed through here rather
 * than by loosening the compiler or asserting non-null at every call site.
 */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

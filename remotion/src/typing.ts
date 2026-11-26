export const lineProgress = (time: number, at: number, duration: number) =>
  Math.max(0, Math.min(1, (time - at) / duration));

export const typedChars = (plain: string, time: number, at: number, duration: number) => {
  const total = Array.from(plain).length;
  const p = lineProgress(time, at, duration);
  return Math.min(total, Math.ceil(p * total));
};

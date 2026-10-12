// Junta classes do Tailwind resolvendo conflitos (a última vence), como nas outras ferramentas.
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export const cn = (...classes) => twMerge(clsx(classes));

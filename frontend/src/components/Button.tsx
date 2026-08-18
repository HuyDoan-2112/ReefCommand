import type { ButtonHTMLAttributes } from 'react';

import { cx } from '@/lib/cx';

import styles from './Button.module.css';

/**
 * The standard button.
 *
 * `type` defaults to "button". The HTML default is "submit", which inside a
 * form makes an unrelated button submit it.
 */

type Variant = 'primary' | 'coral' | 'ghost';

const VARIANTS: Record<Variant, string | undefined> = {
  primary: styles.primary,
  coral: styles.coral,
  ghost: styles.ghost,
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: 'default' | 'small';
}

export function Button({
  variant = 'primary',
  size = 'default',
  className,
  type = 'button',
  ...rest
}: ButtonProps) {
  const classes = cx(styles.root, VARIANTS[variant], size === 'small' && styles.small, className);

  return <button type={type} className={classes} {...rest} />;
}

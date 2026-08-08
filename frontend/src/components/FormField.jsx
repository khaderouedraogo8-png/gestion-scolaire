import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export default function FormField({
  label,
  name,
  type = 'text',
  value,
  onChange,
  error,
  required = false,
  placeholder,
  disabled = false,
  options = [],
  rows = 3,
  helpText,
  className = '',
  ...rest
}) {
  const [showPassword, setShowPassword] = useState(false);
  const inputId = name ? `field-${name}` : undefined;
  const hasError = Boolean(error);
  const isPassword = type === 'password';

  const baseClass = `input ${hasError ? 'border-brique focus:border-brique focus:ring-brique/20' : ''} ${isPassword ? 'pr-10' : ''} ${className}`;

  const renderInput = () => {
    if (type === 'select') {
      return (
        <select
          id={inputId}
          name={name}
          value={value ?? ''}
          onChange={onChange}
          disabled={disabled}
          className={baseClass}
          {...rest}
        >
          <option value="">— Sélectionner —</option>
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      );
    }

    if (type === 'textarea') {
      return (
        <textarea
          id={inputId}
          name={name}
          value={value ?? ''}
          onChange={onChange}
          disabled={disabled}
          placeholder={placeholder}
          rows={rows}
          className={baseClass}
          {...rest}
        />
      );
    }

    if (type === 'checkbox') {
      return (
        <label className="flex items-center gap-2">
          <input
            id={inputId}
            type="checkbox"
            name={name}
            checked={Boolean(value)}
            onChange={onChange}
            disabled={disabled}
            className="h-4 w-4 rounded border-bordure text-or-cachet focus:ring-or-cachet/30"
            {...rest}
          />
          <span className="text-sm text-encre">{label}</span>
        </label>
      );
    }

    return (
      <div className="relative">
        <input
          id={inputId}
          type={isPassword && showPassword ? 'text' : type}
          name={name}
          value={value ?? ''}
          onChange={onChange}
          disabled={disabled}
          placeholder={placeholder}
          className={baseClass}
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-texte-secondaire hover:text-encre"
            aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
    );
  };

  if (type === 'checkbox') {
    return (
      <div>
        {renderInput()}
        {error && <p className="mt-1 text-xs text-brique">{error}</p>}
        {helpText && !error && <p className="mt-1 text-xs text-texte-secondaire">{helpText}</p>}
      </div>
    );
  }

  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="label">
          {label}
          {required && <span className="text-brique"> *</span>}
        </label>
      )}
      {renderInput()}
      {error && <p className="mt-1 text-xs text-brique">{error}</p>}
      {helpText && !error && <p className="mt-1 text-xs text-texte-secondaire">{helpText}</p>}
    </div>
  );
}

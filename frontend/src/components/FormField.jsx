import { useState } from 'react';

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
  const inputId = `field-${name}`;
  const hasError = Boolean(error);

  const baseClass = `input ${hasError ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20' : ''} ${className}`;

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
            className="h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
            {...rest}
          />
          <span className="text-sm text-slate-700">{label}</span>
        </label>
      );
    }

    return (
      <input
        id={inputId}
        type={type}
        name={name}
        value={value ?? ''}
        onChange={onChange}
        disabled={disabled}
        placeholder={placeholder}
        className={baseClass}
        {...rest}
      />
    );
  };

  if (type === 'checkbox') {
    return (
      <div>
        {renderInput()}
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
        {helpText && !error && <p className="mt-1 text-xs text-slate-500">{helpText}</p>}
      </div>
    );
  }

  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="label">
          {label}
          {required && <span className="text-red-500"> *</span>}
        </label>
      )}
      {renderInput()}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      {helpText && !error && <p className="mt-1 text-xs text-slate-500">{helpText}</p>}
    </div>
  );
}

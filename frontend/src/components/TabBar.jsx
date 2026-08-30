export default function TabBar({ tabs, active, onChange, className = '' }) {
  return (
    <div className={`tab-bar ${className}`} role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={active === tab.id ? 'tab-bar-item tab-bar-item-active' : 'tab-bar-item'}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

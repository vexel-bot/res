import { ClickoSelectMenu } from '../../components/ClickoSelectMenu';
/** Local adapter preserves the shared menu's tuple contract and disabled field semantics. */
export function LocalSelect({ value, options, onChange, ariaLabel, disabled }: {
    value: string;
    options: Array<{
        value: string;
        label: string;
    }>;
    onChange: (value: string) => void;
    ariaLabel: string;
    disabled?: boolean;
}) {
    return <fieldset disabled={disabled} className="lp-select"><ClickoSelectMenu label={ariaLabel} value={value} options={options.map(option => [option.value, option.label])} onChange={onChange}/></fieldset>;
}

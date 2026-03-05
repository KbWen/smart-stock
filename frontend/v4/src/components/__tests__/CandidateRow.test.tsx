import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import CandidateRow from '../dashboard/CandidateRow';
import { MemoryRouter } from 'react-router-dom';

const mockStock = {
    ticker: '2330.TW',
    name: '台積電',
    price: 1000,
    change_percent: 1.5,
    rise_score: 85,
    ai_prob: 75,
    v4_signals: {
        squeeze: true,
        golden_cross: true,
        volume_spike: false,
    },
};

describe('CandidateRow', () => {
    it('renders stock info correctly', () => {
        render(
            <MemoryRouter>
                <CandidateRow
                    stock={mockStock as any}
                    isSelected={false}
                    onSelect={() => { }}
                    rowHeight={50}
                />
            </MemoryRouter>
        );

        expect(screen.getByText('2330.TW')).toBeInTheDocument();
        expect(screen.getByText('台積電')).toBeInTheDocument();
        expect(screen.getByText(/Squeeze/i)).toBeInTheDocument();
        expect(screen.getByText('+1')).toBeInTheDocument();
    });
});

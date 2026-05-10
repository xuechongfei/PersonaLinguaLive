import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UploadZone from './UploadZone';

function makeFile(name: string, type: string, size = 100): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('UploadZone', () => {
  it('点击 input 选合法 jpeg 时回调 onFile', () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const input = screen.getByTestId('upload-input') as HTMLInputElement;

    const file = makeFile('a.jpg', 'image/jpeg');
    fireEvent.change(input, { target: { files: [file] } });

    expect(onFile).toHaveBeenCalledWith(file);
  });

  it('drop 不支持的类型时显示错误,且不触发 onFile', () => {
    const onFile = vi.fn();
    render(<UploadZone onFile={onFile} />);
    const dropTarget = screen.getByTestId('upload-zone');

    const file = makeFile('a.heic', 'image/heic');
    fireEvent.drop(dropTarget, { dataTransfer: { files: [file] } });

    expect(onFile).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent(/仅支持/);
  });

  it('dragOver 时切换 high-light 样式', () => {
    render(<UploadZone onFile={() => {}} />);
    const dropTarget = screen.getByTestId('upload-zone');
    fireEvent.dragOver(dropTarget);
    expect(dropTarget.className).toMatch(/border-sky-500|bg-sky-50/);
  });
});

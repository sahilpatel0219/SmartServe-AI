import { Component } from 'react';

/**
 * Last line of defence: without this, a render throw anywhere below the boundary
 * unmounts the whole subtree, leaving a blank screen with only a console trace.
 * Wraps each route so one broken page doesn't take down the whole shell.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info?.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="alert alert-danger" style={{ margin: 'var(--space-6)' }}>
        <i className="bi bi-exclamation-octagon-fill" />
        <div style={{ flex: 1 }}>
          <div className="fw-semi">This screen crashed while rendering</div>
          <div className="text-sm" style={{ marginTop: 4 }}>
            {String(this.state.error?.message || this.state.error)}
          </div>
        </div>
        <button type="button" className="btn btn-sm btn-outline" onClick={this.reset}>
          Retry
        </button>
      </div>
    );
  }
}

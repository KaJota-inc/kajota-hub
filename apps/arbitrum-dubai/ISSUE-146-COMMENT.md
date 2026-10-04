Is the hostio dependency still the blocker here? Reading the current code I
think these can be restored today, but I'd rather check than assume.

`RawCall` already does exactly what this issue asks for, without any special
hostio support:

- `stylus-sdk/src/call/raw.rs:18-19` keeps `offset: usize` and
  `size: Option<usize>` on the struct
- `:143` / `:151` expose `limit_return_data(offset, size)` and
  `skip_return_data()` — the same shape as the `limit_revert_data` /
  `skip_revert_data` in the issue body
- `:215` applies them at `self.host.read_return_data(self.offset, self.size)`

`RawDeploy` reads its revert data through the same path but hardcodes the
arguments — `stylus-sdk/src/deploy/raw.rs:108`:

```rust
if contract.is_zero() {
    return Err(host.read_return_data(0, None));
}
```

and `Host::read_return_data(&self, offset: usize, size: Option<usize>)`
(`stylus-core/src/host.rs:87`) already takes what's needed. `create1` /
`create2` only report `revert_data_len`; the bytes come back afterwards via
`read_return_data`, which is RETURNDATACOPY, and that's where `RawCall`
does its limiting.

So unless I'm missing something about deploy-side semantics, restoring the
two methods looks like mirroring `RawCall`: add the two fields, re-add the
methods with the doc comments above, and pass them through at `:108`.

Happy to open a PR for that with tests if you'd like it — and equally happy
to be told the hostio note still stands and I've misread it.

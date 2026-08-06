# Episode ID Addressing

## Format

`<branch_key>:<seq>`

The `@episode` header is the source of the episode ID. The compiler does not derive or compare it against the file path.

Examples:

```
main:01
main:02
main/bad/001:01
main/route/001:01
main/minor/11_a:01
```

Use the full ID in `@next` leaves:

```
@gate { @next main:02 }

@gate {
  @if (A.fail): @next main/bad/001:01
  @else: @next main:02
}
```

Keep sequence numbers zero-padded to two digits for consistent authoring. Cross-file target existence is a content-review concern; the compiler does not verify `@next` targets.

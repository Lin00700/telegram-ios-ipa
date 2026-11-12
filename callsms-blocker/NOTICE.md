# Third-party notices

## Mobile prefix data

The file `Resources/prefix_ranges.dat` and the virtual-prefix list are derived from
`phone.dat` in [ls0f/phone](https://github.com/ls0f/phone) (upstream header `2312`).
That repository's README states the database is MIT licensed:

https://opensource.org/licenses/MIT

The original `phone.dat` is not vendored. `scripts/build_prefix_db.py` records the
upstream SHA-256 in `Resources/SOURCE.json`. One upstream area code, `00479` for
锡林郭勒, is stored as `0479`.

```
MIT License

Copyright (c) ls0f/phone contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Reference projects

The app's behavior follows public iOS extension APIs. The designs of these
projects were read so the extension points, local rule shape, and Call Directory
ordering would match what already works. Their source files were not copied.

- [boommanpro/ios-sms-guard](https://github.com/boommanpro/ios-sms-guard) — MIT
- [afterxleep/Bouncer](https://github.com/afterxleep/Bouncer) — MIT
- [ekrmsnr/smspam](https://github.com/ekrmsnr/smspam) — MIT
- [Rex-xingjl/CallKitDemo](https://github.com/Rex-xingjl/CallKitDemo) — no license file; only the public Call Directory ordering pattern was used as a reference

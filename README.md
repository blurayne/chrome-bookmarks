# Browser Bookmark Search extension for [Ulauncher](https://ulauncher.io/).

## Abstract

Find and launch your browser bookmarks within multiple profiles through Ulauncher. 

That means you could have one profile for work and one for private stuff.

When you find a bookmark within your work profile it is opened by work browser vice versum.

## Credits

This work is based on two other extensions I modified to my needs

- [Google Chrome bookmarks](https://github.com/nortmas/Chrome-bookmarks) by  Dimitry Antonenko (nortamas) and Bruna Baz 
- [Bookmarks Fuzzy Search](https://github.com/man0xff/ulauncher-bookmarks) by Oleg Kovalev (man0xff)

## Development

We are using [Just](https://github.com/casey/just) as better make alternative – install by:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to DEST
```

Prepare a symlink to your ulauncher projects directory:

```bash
just prepare-dev
```

Use one terminal to:

```.bash
just run-dev-ulauncher
```

And another terminal to:

```bash
just run-dev-extension
```

And you’re ready to go!

## Todo

- [ ] Alternative Action: Open with other browser/profiles
- [ ] Better browser/profile detection
- [ ] Make fallbacks configurable by preferences
- [ ] Support Firefox (and other browsers)
- [ ] Set default browser
- [ ] Reset profile selection if using non-standard browser

## Trackback

- http://docs.ulauncher.io/en/latest/extensions/debugging.html
- [ULauncher Exensions](https://ext.ulauncher.io/)



## License

https://www.iconfinder.com/search/?q=bookmark&price=free&license=1&size=128
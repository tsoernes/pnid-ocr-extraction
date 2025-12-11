# Transfer Repository to Bouvet Organization

## Steps to Transfer

1. **Go to Repository Settings**
   - Navigate to: https://github.com/tsoernes/pnid-ocr-extraction/settings

2. **Scroll to Danger Zone**
   - Find the "Transfer ownership" section at the bottom

3. **Transfer to Bouvet**
   - Click "Transfer"
   - Type: `bouvet/pnid-ocr-extraction`
   - Confirm the repository name: `pnid-ocr-extraction`
   - Click "I understand, transfer this repository"

4. **Update Local Remote** (after transfer)
   ```bash
   git remote set-url origin git@github.com:bouvet/pnid-ocr-extraction.git
   ```

## Alternative: Via GitHub CLI

```bash
# You may need admin access to Bouvet org for this to work
gh repo transfer tsoernes/pnid-ocr-extraction bouvet
```

## After Transfer

Update the README.md to reflect the new repository location:
- Clone URL: `https://github.com/bouvet/pnid-ocr-extraction.git`
- All documentation references

## Note

If you don't have permission to transfer directly, you can:
1. Request a Bouvet org admin to fork/import the repository
2. Or request admin access to create repos in the Bouvet org
